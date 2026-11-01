"""Temporary hosted CI failure check; keep this on the validation branch."""

import unittest


class CIFailureProbe(unittest.TestCase):
    def test_failure_is_not_ignored(self):
        self.fail("Intentional hosted CI verification failure")
