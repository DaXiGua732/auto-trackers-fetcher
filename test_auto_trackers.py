#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""auto-trackers-fetcher.py 的回归测试：python -m unittest -v test_auto_trackers

测试都落在接口上：
- 纯函数（parse_tracker / 质检策略 / plan_update）：直接断言，不联网、不碰磁盘、不记日志；
- 本轮资源（RunResources）：喂一个假的计算函数，验证缓存命中与「一轮一实例」；
- 文件读写（read_old_trackers / save_trackers）：临时目录即替身；
- 组流水线（process_tracker_group）：注入拉取/质检，验证「不写就真的没动旧文件」与写失败。
"""

import importlib.util
import os
import tempfile
import unittest
from unittest import mock

_SPEC = importlib.util.spec_from_file_location(
    "auto_trackers_fetcher",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto-trackers-fetcher.py"),
)
tf = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(tf)


def tracker(url):
    """测试里造一条 Tracker，口径与解析一致。"""
    parsed = tf.parse_tracker(url)
    assert parsed is not None, url
    return parsed


def trackers(*urls):
    return {tracker(url) for url in urls}


class ParseTest(unittest.TestCase):
    def test_parses_scheme_host_and_trailing_slash(self):
        self.assertEqual(
            tracker("  UDP://Tracker.OpenTrackr.ORG:1337/announce/  "),
            tf.Tracker("udp", "tracker.opentrackr.org", "udp://tracker.opentrackr.org:1337/announce"),
        )

    def test_rejects_untrackable_input(self):
        for bad in ("ftp://x.com/a", "tracker.example.com:6969/announce", "", "   ", "http://",
                    "wss://tracker.openwebtorrent.com:443/announce"):
            self.assertIsNone(tf.parse_tracker(bad), bad)

    def test_skips_comments_and_dedupes(self):
        text = "# comment\n\nudp://A.B:1/announce\nudp://a.b:1/announce/\nftp://x/y\n"
        self.assertEqual(tf.parse_tracker_lines(text), trackers("udp://a.b:1/announce"))


class PolicyTest(unittest.TestCase):
    """质检判定是纯规则：不联网、不睡、不发请求。"""

    @staticmethod
    def _error(status):
        """造一个带 response 的 RequestException；status=None 表示网络错。"""
        error = tf.requests.RequestException("boom")
        error.response = None if status is None else mock.Mock(status_code=status)
        return error

    def test_retryable_only_for_transient_failures(self):
        self.assertTrue(tf.retryable(self._error(None)))  # 网络错
        self.assertTrue(tf.retryable(self._error(500)))
        self.assertTrue(tf.retryable(self._error(503)))
        self.assertTrue(tf.retryable(self._error(429)))
        self.assertFalse(tf.retryable(self._error(404)))  # 永久错误，重试只是白等
        self.assertFalse(tf.retryable(self._error(400)))

    def test_retry_delay_is_exponential_with_jitter(self):
        self.assertTrue(2.0 <= tf.retry_delay(1) < 3.0)
        self.assertTrue(4.0 <= tf.retry_delay(2) < 5.0)

    def test_verdict_for_status(self):
        self.assertEqual(tf.verdict_for(None), tf.Verdict(False, True, "连接失败/超时"))
        self.assertFalse(tf.verdict_for(404).valid)
        self.assertFalse(tf.verdict_for(500).valid)
        self.assertTrue(tf.verdict_for(400).valid)  # 400 说明服务器活着
        self.assertTrue(tf.verdict_for(200).valid)


class ResourcesTest(unittest.TestCase):
    """RunResources：一轮一个实例，实例之间互不串味。"""

    def test_verdict_is_computed_once_per_instance(self):
        calls = []

        def fake(url):
            calls.append(url)
            return tf.Verdict(True, True, "存活")

        resources = tf.RunResources()
        first = resources.verdict("http://a.example/announce", fake)
        second = resources.verdict("http://a.example/announce", fake)
        self.assertEqual(calls, ["http://a.example/announce"])
        self.assertEqual(first, second)

    def test_fresh_instance_recomputes(self):
        calls = []

        def fake(url):
            calls.append(url)
            return tf.Verdict(True, True, "存活")

        tf.RunResources().verdict("http://a.example/announce", fake)
        tf.RunResources().verdict("http://a.example/announce", fake)
        self.assertEqual(len(calls), 2)

    def test_failed_fetch_is_not_cached(self):
        calls = []

        def fake(url):
            calls.append(url)
            return trackers("udp://a.b:1/announce") if len(calls) > 1 else set()

        resources = tf.RunResources()
        self.assertEqual(resources.fetch("http://src", fake), set())
        self.assertEqual(resources.fetch("http://src", fake), trackers("udp://a.b:1/announce"))
        self.assertEqual(calls, ["http://src", "http://src"])

    def test_resolved_is_cached(self):
        calls = []

        def fake(hostname):
            calls.append(hostname)
            return (True, "1.2.3.4")

        resources = tf.RunResources()
        self.assertEqual(resources.resolved("a.example", fake), (True, "1.2.3.4"))
        self.assertEqual(resources.resolved("a.example", fake), (True, "1.2.3.4"))
        self.assertEqual(calls, ["a.example"])


class VerdictTest(unittest.TestCase):
    def test_udp_passes_on_dns_alone_and_says_so(self):
        with mock.patch.object(tf, "resolve_global", return_value=(True, "1.2.3.4")):
            udp = tf.validate_tracker_url(tracker("udp://b.example:1/announce"), tf.RunResources())
        self.assertTrue(udp.valid)
        self.assertFalse(udp.probed)  # 「未探测 N 条」靠这个事实算，不靠日志文案

    def test_http_dead_tracker_is_filtered(self):
        with mock.patch.object(tf, "resolve_global", return_value=(True, "1.2.3.4")), \
                mock.patch.object(tf, "probe_http_tracker", return_value=404):
            verdict = tf.validate_tracker_url(tracker("http://b.example/announce"), tf.RunResources())
        self.assertFalse(verdict.valid)


class PlanTest(unittest.TestCase):
    """写盘策略是纯函数：所有分支都在这里断言，不需要 mock，也不需要临时目录。"""

    OLD = trackers(*["udp://t%d:1/announce" % i for i in range(20)])

    def test_every_write_decision_without_io(self):
        cases = [
            # 场景, raw, valid, old, dry_run, 期望 write, 期望 ok, 日志里该有的字样
            ("拉取为空", set(), set(), self.OLD, False, False, False, "未获取到任何数据"),
            ("质检全灭", trackers("udp://x:1/announce"), set(), self.OLD, False, False, False, "质检后无有效"),
            ("首次生成", trackers("udp://x:1/announce"), trackers("udp://x:1/announce"), set(), False, True, True, "首次生成"),
            ("无变化", self.OLD, self.OLD, self.OLD, False, False, True, "列表无变化"),
            ("少量失效", self.OLD, trackers(*["udp://t%d:1/announce" % i for i in range(1, 20)]), self.OLD, False, True, True, "移除/失效 1"),
            ("骤降", self.OLD, trackers(*["udp://t%d:1/announce" % i for i in range(5)]), self.OLD, False, False, False, "骤降"),
            ("干跑", trackers("udp://x:1/announce"), trackers("udp://x:1/announce"), set(), True, False, True, "干跑模式"),
        ]
        for label, raw, valid, old, dry_run, want_write, want_ok, text in cases:
            with self.subTest(label):
                plan = tf.plan_update(raw, valid, old, dry_run)
                self.assertEqual((plan.write, plan.ok), (want_write, want_ok))
                self.assertIn(text, " ".join(t for _, t in plan.logs))


class FileTest(unittest.TestCase):
    def test_save_is_sorted_by_url_lf_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "trackers.txt")
            self.assertTrue(tf.save_trackers(path, trackers("udp://b:1/announce", "udp://a:1/announce")))
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"udp://a:1/announce\nudp://b:1/announce\n")
            self.assertEqual(os.listdir(d), ["trackers.txt"])

    def test_old_file_is_read_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "trackers.txt")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write("UDP://A.B:1/announce/\n# 手写的注释\n")
            self.assertEqual(tf.read_old_trackers(path), trackers("udp://a.b:1/announce"))


class GroupTest(unittest.TestCase):
    """组流水线的接线：plan 说不写，旧文件就必须原样不动。"""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name
        self.path = os.path.join(self.dir, "trackers.txt")
        self.old = ["udp://t%d:1/announce" % i for i in range(20)]
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(line + "\n" for line in self.old))

    def _content(self):
        with open(self.path, encoding="utf-8") as f:
            return f.read()

    def _old_lines(self):
        return "".join(line + "\n" for line in self.old)

    def _run(self, fetch, validate=False, check=None, path=None):
        kwargs = {"validate": validate, "fetch": fetch}
        if check is not None:
            kwargs["check"] = check
        return tf.process_tracker_group("T", ["http://src"], path or self.path, tf.RunResources(), **kwargs)

    def test_empty_fetch_keeps_old_file(self):
        self.assertFalse(tf.process_tracker_group("T", [], self.path, tf.RunResources()))
        self.assertEqual(self._content(), self._old_lines())

    def test_big_drop_keeps_old_file(self):
        self.assertFalse(self._run(lambda urls, resources: trackers(*self.old[:5])))
        self.assertEqual(self._content(), self._old_lines())

    def test_all_invalid_keeps_old_file(self):
        self.assertFalse(self._run(lambda urls, resources: trackers("udp://new:1/announce"),
                                   validate=True,
                                   check=lambda trackers_, resources, max_workers: set()))
        self.assertEqual(self._content(), self._old_lines())

    def test_small_drop_is_written(self):
        keep = trackers(*self.old[1:])
        self.assertTrue(self._run(lambda urls, resources: keep))
        self.assertEqual(self._content(), "\n".join(sorted(t.url for t in keep)) + "\n")

    def test_write_failure_is_reported(self):
        missing = os.path.join(self.dir, "no-such-dir", "trackers.txt")
        self.assertFalse(self._run(lambda urls, resources: trackers("udp://new:1/announce"), path=missing))
        self.assertFalse(os.path.exists(os.path.dirname(missing)))  # 原子写不留残骸


if __name__ == "__main__":
    unittest.main()