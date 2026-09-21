"""The API's own error message must reach the caller.

THE DEFECT (found 2026-09-20)
=============================
`_handle_error` answered 401, 402 and 429 with a fixed sentence and threw the
response body away:

    if status_code == 429:
        raise RateLimitError("Rate limit exceeded — wait or upgrade your plan")

Those are the three statuses that carry the most actionable text this API
produces, and free.ai deliberately puts the entire remedy in the message
because the structured fields around it are not forwarded to every caller.

A 429 from this API can mean at least five different things: the daily pool
is spent (with the number remaining), the account is unverified, a per-tool
cap was hit, a monthly API limit was reached (with its reset date), or a
premium model was requested on a free account. The SDK reported all five as
"Rate limit exceeded — wait or upgrade your plan", which names none of them
and tells the caller to do nothing useful.

Measured against the live API before and after:

    premium model, anonymous
      before  "Insufficient tokens — buy more at https://free.ai/pricing/"
      after   "This chat request needs ~16,877 tokens. You have 6,000
               available (0 balance + 6,000 daily pool, shortfall 10,877)"
               + details: estimated_cost, available, shortfall, upgrade_url

    video, anonymous
      before  "Rate limit exceeded — wait or upgrade your plan"
      after   "Sign up free: 30,000 tokens/day to use this tool."
               + details: requires_signup=True, daily_remaining=6000

WHAT THIS PINS
==============
1. The body's message wins over the hardcoded fallback on 401/402/429.
2. The fallback is still there for a body that carries no message (the
   negative control: deleting the fallbacks entirely would leave a caller
   with an empty error string).
3. Both body shapes parse -- flat `{"error": "..."}` and the nested
   `{"error": {"error": "...", "requires_signup": true}}` form, which the old
   fallthrough would have stringified as a raw dict.
4. `error_id` is captured and appears in `str(exc)`, because it is the only
   thing support can look up.
5. The exception CLASS still tracks the status, so existing `except
   InsufficientCreditsError` code keeps working.
6. A 2xx raises nothing.
"""
import unittest

from freeai.client import _handle_error, _parse_error_body
from freeai.exceptions import (FreeAIError, AuthenticationError,
                               RateLimitError, InsufficientCreditsError)


def _raised(status, body):
    try:
        _handle_error(status, body)
    except FreeAIError as exc:
        return exc
    return None


class TestServerMessageWins(unittest.TestCase):
    def test_429_keeps_the_real_reason(self):
        exc = _raised(429, '{"error":"Sign up free: 30,000 tokens/day to use '
                           'this tool.","error_id":"e31fa892"}')
        self.assertIsInstance(exc, RateLimitError)
        self.assertIn('30,000 tokens/day', exc.message)
        self.assertNotIn('Rate limit exceeded', exc.message)

    def test_402_keeps_the_shortfall_arithmetic(self):
        exc = _raised(402, '{"error":"This chat request needs ~16,877 tokens. '
                           'You have 6,000 available."}')
        self.assertIsInstance(exc, InsufficientCreditsError)
        self.assertIn('16,877', exc.message)

    def test_401_keeps_the_real_reason(self):
        exc = _raised(401, '{"error":"API key was revoked on 2026-09-01."}')
        self.assertIsInstance(exc, AuthenticationError)
        self.assertIn('revoked', exc.message)


class TestFallbackSurvives(unittest.TestCase):
    """Negative control.

    Preferring the body must not mean an empty error when there is no body --
    deleting the fallback table would pass every test above.
    """

    def test_empty_body_uses_the_fallback(self):
        for status, cls, needle in ((401, AuthenticationError, 'API key'),
                                    (402, InsufficientCreditsError, 'tokens'),
                                    (429, RateLimitError, 'Rate limit')):
            exc = _raised(status, '')
            self.assertIsInstance(exc, cls)
            self.assertIn(needle, exc.message)

    def test_unknown_status_still_reports(self):
        exc = _raised(503, '')
        self.assertIsInstance(exc, FreeAIError)
        self.assertTrue(exc.message)


class TestBodyShapes(unittest.TestCase):
    def test_nested_error_object_is_unwrapped(self):
        exc = _raised(429, '{"error":{"error":"Sign up free: 30,000 tokens/day.",'
                           '"requires_signup":true,"daily_remaining":6000},'
                           '"error_id":"2a7bfa7c"}')
        self.assertEqual(exc.message, 'Sign up free: 30,000 tokens/day.')
        self.assertNotIn('{', exc.message, 'a dict leaked into the message')
        self.assertTrue(exc.details.get('requires_signup'))
        self.assertEqual(exc.details.get('daily_remaining'), 6000)

    def test_detail_key_is_read(self):
        exc = _raised(400, '{"detail":"That face photo is too large."}')
        self.assertIn('too large', exc.message)

    def test_fastapi_validation_list(self):
        exc = _raised(422, '{"detail":[{"loc":["body","x"],"msg":"Field required"}]}')
        self.assertIn('Field required', exc.message)

    def test_non_json_body_is_not_swallowed(self):
        exc = _raised(502, '<html>502 Bad Gateway</html>')
        self.assertIn('502', exc.message)


class TestErrorId(unittest.TestCase):
    def test_error_id_is_captured_and_printed(self):
        exc = _raised(429, '{"error":"nope","error_id":"4e80277d"}')
        self.assertEqual(exc.error_id, '4e80277d')
        self.assertIn('4e80277d', str(exc),
                      'the error_id is the only thing support can look up; it '
                      'has to be in the text a traceback prints')

    def test_error_id_is_not_duplicated_into_details(self):
        exc = _raised(429, '{"error":"nope","error_id":"4e80277d"}')
        self.assertNotIn('error_id', exc.details)

    def test_absent_error_id_does_not_decorate_the_message(self):
        exc = _raised(429, '{"error":"nope"}')
        self.assertEqual(str(exc), 'nope')


class TestNoRaiseOnSuccess(unittest.TestCase):
    def test_2xx_returns(self):
        self.assertIsNone(_handle_error(200, '{"ok":true}'))
        self.assertIsNone(_handle_error(204, ''))

    def test_details_is_always_a_dict(self):
        """Callers .get() on it without guarding."""
        self.assertEqual(_raised(500, 'boom').details, {})


if __name__ == '__main__':
    unittest.main()
