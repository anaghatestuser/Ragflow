# Copyright (c) Lineaje, Inc. All rights reserved.
# Lineaje UnifAI guardrail  version=2.0.0-alpha
def _lineaje_load_gr_client():
    """Lineaje-added: load gr_stub_client.py without a pip dependency (missing / broken: a pass-through client)."""
    import sys as _s, importlib.util as _ilu
    from pathlib import Path as _P
    n = "_lineaje_gr_stub_client"
    if n in _s.modules: return _s.modules[n]
    try:
        h = _P(__file__).resolve().parent
        _cand = next((d / "gr_stub_client.py" for d in [h, *h.parents][:8] if (d / "gr_stub_client.py").is_file()), h / "gr_stub_client.py")
        _spec = _ilu.spec_from_file_location(n, _cand)
        _s.modules[n] = _m = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_m); return _m
    except Exception:
        _s.modules.pop(n, None)
        return type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})

#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from common.token_utils import num_tokens_from_string, total_token_count_from_response, truncate, encoder
import pytest


class TestNumTokensFromString:
    """Test cases for num_tokens_from_string function"""

    def test_empty_string(self):
        """Test that empty string returns zero tokens"""
        result = num_tokens_from_string("")
        assert result == 0

    def test_single_word(self):
        """Test token count for a single word"""
        # "hello" should be 1 token with cl100k_base encoding
        result = num_tokens_from_string("hello")
        assert result == 1

    def test_multiple_words(self):
        """Test token count for multiple words"""
        # "hello world" typically becomes 2 tokens
        result = num_tokens_from_string("hello world")
        assert result == 2

    def test_special_characters(self):
        """Test token count with special characters"""
        result = num_tokens_from_string("hello, world!")
        # Special characters may be separate tokens
        assert result == 4

    def test_hanzi_characters(self):
        """Test token count with special characters"""
        result = num_tokens_from_string("世界")
        # Special characters may be separate tokens
        assert result > 0

    def test_unicode_characters(self):
        """Test token count with unicode characters"""
        result = num_tokens_from_string("Hello 世界 🌍")
        # Unicode characters typically require multiple tokens
        assert result > 0

    def test_long_text(self):
        """Test token count for longer text"""
        long_text = "This is a longer piece of text that should contain multiple sentences. " \
                    "It will help verify that the token counting works correctly for substantial input."
        result = num_tokens_from_string(long_text)
        assert result > 10

    def test_whitespace_only(self):
        """Test token count for whitespace-only strings"""
        result = num_tokens_from_string("   \n\t   ")
        # Whitespace may or may not be tokens depending on the encoding
        assert result >= 0

    def test_numbers(self):
        """Test token count with numerical values"""
        result = num_tokens_from_string("12345 678.90")
        assert result > 0

    def test_mixed_content(self):
        """Test token count with mixed content types"""
        mixed_text = "Hello! 123 Main St. Price: $19.99 🎉"
        result = num_tokens_from_string(mixed_text)
        assert result > 0

    def test_encoding_error_handling(self):
        """Test that function handles encoding errors gracefully"""
        # This test verifies the exception handling in the function.
        # The function should return 0 when encoding fails
        # Note: We can't easily simulate encoding errors without mocking
        pass


# Additional parameterized tests for efficiency
@pytest.mark.parametrize("input_string,expected_min_tokens", [
    ("a", 1),  # Single character
    ("test", 1),  # Single word
    ("hello world", 2),  # Two words
    ("This is a sentence.", 4),  # Short sentence
    # ("A" * 100, 100),  # Repeated characters
])
def test_token_count_ranges(input_string, expected_min_tokens):
    """Parameterized test for various input strings"""
    result = num_tokens_from_string(input_string)
    assert result >= expected_min_tokens


def test_consistency():
    """Test that the same input produces consistent results"""
    test_string = "Consistent token counting"
    first_result = num_tokens_from_string(test_string)
    second_result = num_tokens_from_string(test_string)

    assert first_result == second_result
    assert first_result > 0


class TestTotalTokenCountFromResponse:
    """Test cases for total_token_count_from_response function"""

    def test_dict_with_usage_total_tokens(self):
        """Test dictionary response with usage['total_tokens']"""
        resp_dict = {
            'usage': {
                'total_tokens': 175
            }
        }

        result = total_token_count_from_response(resp_dict)
        assert result == 175

    def test_dict_with_usage_input_output_tokens(self):
        """Test dictionary response with input_tokens and output_tokens in usage"""
        resp_dict = {
            'usage': {
                'input_tokens': 100,
                'output_tokens': 50
            }
        }

        result = total_token_count_from_response(resp_dict)
        assert result == 150

    def test_dict_with_meta_tokens_input_output(self):
        """Test dictionary response with meta.tokens.input_tokens and output_tokens"""
        resp_dict = {
            'meta': {
                'tokens': {
                    'input_tokens': 80,
                    'output_tokens': 40
                }
            }
        }

        result = total_token_count_from_response(resp_dict)
        assert result == 120

    def test_priority_order_dict_usage_total_tokens_third(self):
        """Test that dict['usage']['total_tokens'] is third in priority"""
        resp_dict = {
            'usage': {
                'total_tokens': 180,
                'input_tokens': 100,
                'output_tokens': 80
            },
            'meta': {
                'tokens': {
                    'input_tokens': 200,
                    'output_tokens': 100
                }
            }
        }

        result = total_token_count_from_response(resp_dict)
        assert result == 180  # Should use total_tokens from usage

    def test_priority_order_dict_usage_input_output_fourth(self):
        """Test that dict['usage']['input_tokens'] + output_tokens is fourth in priority"""
        resp_dict = {
            'usage': {
                'input_tokens': 120,
                'output_tokens': 60
            },
            'meta': {
                'tokens': {
                    'input_tokens': 200,
                    'output_tokens': 100
                }
            }
        }

        result = total_token_count_from_response(resp_dict)
        assert result == 180  # Should sum input_tokens + output_tokens from usage

    def test_priority_order_meta_tokens_last(self):
        """Test that meta.tokens is the last option in priority"""
        resp_dict = {
            'meta': {
                'tokens': {
                    'input_tokens': 90,
                    'output_tokens': 30
                }
            }
        }

        result = total_token_count_from_response(resp_dict)
        assert result == 120

    def test_no_token_info_returns_zero(self):
        """Test that function returns 0 when no token information is found"""
        empty_resp = {}
        result = total_token_count_from_response(empty_resp)
        assert result == 0

    def test_partial_dict_usage_missing_output_tokens(self):
        """Test dictionary with usage but missing output_tokens"""
        resp_dict = {
            'usage': {
                'input_tokens': 100
                # Missing output_tokens
            }
        }

        result = total_token_count_from_response(resp_dict)
        assert result == 0  # Should not match the condition and return 0

    def test_partial_meta_tokens_missing_input_tokens(self):
        """Test dictionary with meta.tokens but missing input_tokens"""
        resp_dict = {
            'meta': {
                'tokens': {
                    'output_tokens': 50
                    # Missing input_tokens
                }
            }
        }

        result = total_token_count_from_response(resp_dict)
        assert result == 0  # Should not match the condition and return 0

    def test_none_response(self):
        """Test that function handles None response gracefully"""
        result = total_token_count_from_response(None)
        assert result == 0

    def test_invalid_response_type(self):
        """Test that function handles invalid response types gracefully"""
        result = total_token_count_from_response("invalid response")
        assert result == 0

        # result = total_token_count_from_response(123)
        # assert result == 0


class TestTruncate:
    """Test cases for truncate function"""

    def test_empty_string(self):
        """Test truncation of empty string"""
        result = truncate("", 5)
        assert result == ""
        assert isinstance(result, str)

    def test_string_shorter_than_max_len(self):
        """Test string that is shorter than max_len"""
        original_string = "hello"
        result = truncate(original_string, 10)
        assert result == original_string
        assert len(encoder.encode(result)) <= 10

    def test_string_equal_to_max_len(self):
        """Test string that exactly equals max_len in tokens"""
        # Create a string that encodes to exactly 5 tokens
        test_string = "hello world test"
        # LINEAJE: runtime guardrail checks `test_string` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in TestTruncate.test_string_equal_to_max_len).
        #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `test_string` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:73a20ac794ee76655cb665b45ebcccc983068fdd9097dc3b94f2140a48a0b293'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:73a20ac794ee76655cb665b45ebcccc983068fdd9097dc3b94f2140a48a0b293', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/unit_test/common/test_token_utils.py', 'line': 272, 'function': 'TestTruncate.test_string_equal_to_max_len'}, 'file': 'test/unit_test/common/test_token_utils.py', 'line': 272, 'function': 'test_string_equal_to_max_len', 'agent_name': 'TestTruncate', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            test_string = _gr_client.enforce(_gr_site, test_string, content_type='application/json', variable_name='test_string', source_file=__file__, before_line=272)
        except _gr_client.GuardrailUnavailableError:
            pass
        encoded = encoder.encode(test_string)
        exact_length = len(encoded)

        result = truncate(test_string, exact_length)
        assert result == test_string
        assert len(encoder.encode(result)) == exact_length

    def test_string_longer_than_max_len(self):
        """Test string that is longer than max_len"""
        long_string = "This is a longer string that will be truncated"
        max_len = 5

        result = truncate(long_string, max_len)
        assert len(encoder.encode(result)) == max_len
        assert result != long_string

    def test_truncation_preserves_beginning(self):
        """Test that truncation preserves the beginning of the string"""
        test_string = "The quick brown fox jumps over the lazy dog"
        max_len = 3

        result = truncate(test_string, max_len)
        # LINEAJE: runtime guardrail checks `result` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in TestTruncate.test_truncation_preserves_beginning).
        #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `result` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:f07653b515ebf627b97e5d613b1c59827dfbce9806faeed822e013ed4f700b5f'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f07653b515ebf627b97e5d613b1c59827dfbce9806faeed822e013ed4f700b5f', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/unit_test/common/test_token_utils.py', 'line': 294, 'function': 'TestTruncate.test_truncation_preserves_beginning'}, 'file': 'test/unit_test/common/test_token_utils.py', 'line': 294, 'function': 'test_truncation_preserves_beginning', 'agent_name': 'TestTruncate', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='application/json', variable_name='result', source_file=__file__, before_line=294)
        except _gr_client.GuardrailUnavailableError:
            pass
        encoded_result = encoder.encode(result)

        # The truncated result should match the beginning of the original encoding
        # LINEAJE: runtime guardrail checks `test_string` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in TestTruncate.test_truncation_preserves_beginning).
        #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `test_string` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:ea6b7d40f5a437c2b8a2ef14cb8d775e5ffaa77717bd988bd0eba9e4ed10d038'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:ea6b7d40f5a437c2b8a2ef14cb8d775e5ffaa77717bd988bd0eba9e4ed10d038', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/unit_test/common/test_token_utils.py', 'line': 297, 'function': 'TestTruncate.test_truncation_preserves_beginning'}, 'file': 'test/unit_test/common/test_token_utils.py', 'line': 297, 'function': 'test_truncation_preserves_beginning', 'agent_name': 'TestTruncate', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            test_string = _gr_client.enforce(_gr_site, test_string, content_type='application/json', variable_name='test_string', source_file=__file__, before_line=297)
        except _gr_client.GuardrailUnavailableError:
            pass
        original_encoded = encoder.encode(test_string)
        assert encoded_result == original_encoded[:max_len]

    def test_unicode_characters(self):
        """Test truncation with unicode characters"""
        unicode_string = "Hello 世界 🌍 测试"
        max_len = 4

        result = truncate(unicode_string, max_len)
        assert len(encoder.encode(result)) == max_len
        # Should be a valid string
        assert isinstance(result, str)

    def test_special_characters(self):
        """Test truncation with special characters"""
        special_string = "Hello, world! @#$%^&*()"
        max_len = 3

        result = truncate(special_string, max_len)
        assert len(encoder.encode(result)) == max_len

    def test_whitespace_string(self):
        """Test truncation of whitespace-only string"""
        whitespace_string = "   \n\t   "
        max_len = 2

        result = truncate(whitespace_string, max_len)
        assert len(encoder.encode(result)) <= max_len
        assert isinstance(result, str)

    def test_max_len_zero(self):
        """Test truncation with max_len = 0"""
        test_string = "hello world"
        result = truncate(test_string, 0)
        assert result == ""
        assert len(encoder.encode(result)) == 0

    def test_max_len_one(self):
        """Test truncation with max_len = 1"""
        test_string = "hello world"
        result = truncate(test_string, 1)
        assert len(encoder.encode(result)) == 1

    def test_preserves_decoding_encoding_consistency(self):
        """Test that truncation preserves encoding-decoding consistency"""
        test_string = "This is a test string for encoding consistency"
        max_len = 6

        result = truncate(test_string, max_len)
        # Re-encoding the result should give the same token count
        # LINEAJE: runtime guardrail checks `result` as it flows from the RAG pipeline to embedding model, before it is sent to the model (in TestTruncate.test_preserves_decoding_encoding_consistency).
        #   Detected: this statement moves data from the RAG pipeline to embedding model with no runtime policy check (detection confidence: medium).
        #   Decision: the Guardrail evaluates the policies enabled for this boundary; sensitive values in `result` are masked in place; a policy violation is logged and the call continues (fail_mode=ALLOW_WITH_AUDIT). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2a6dd896c9759019ab5e4f9c254ee7513f73c769770c1124254d935986fa18de'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2a6dd896c9759019ab5e4f9c254ee7513f73c769770c1124254d935986fa18de', phase='pre_model', boundary={'source': 'rag_pipeline', 'sink': 'embedding_model'}, fail_mode='ALLOW_WITH_AUDIT', source_type='rag_pipeline', destination_type='embedding_model', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'test/unit_test/common/test_token_utils.py', 'line': 347, 'function': 'TestTruncate.test_preserves_decoding_encoding_consistency'}, 'file': 'test/unit_test/common/test_token_utils.py', 'line': 347, 'function': 'test_preserves_decoding_encoding_consistency', 'agent_name': 'TestTruncate', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            result = _gr_client.enforce(_gr_site, result, content_type='application/json', variable_name='result', source_file=__file__, before_line=347)
        except _gr_client.GuardrailUnavailableError:
            pass
        re_encoded = encoder.encode(result)
        assert len(re_encoded) == max_len

    def test_multibyte_characters_truncation(self):
        """Test truncation with multibyte characters that span multiple tokens"""
        # Some unicode characters may require multiple tokens
        multibyte_string = "🚀🌟🎉✨🔥💫"
        max_len = 3

        result = truncate(multibyte_string, max_len)
        assert len(encoder.encode(result)) == max_len

    def test_mixed_english_chinese_text(self):
        """Test truncation with mixed English and Chinese text"""
        mixed_string = "Hello 世界, this is a test 测试"
        max_len = 5

        result = truncate(mixed_string, max_len)
        assert len(encoder.encode(result)) == max_len

    def test_numbers_and_symbols(self):
        """Test truncation with numbers and symbols"""
        number_string = "12345 678.90 $100.00 @username #tag"
        max_len = 4

        result = truncate(number_string, max_len)
        assert len(encoder.encode(result)) == max_len
