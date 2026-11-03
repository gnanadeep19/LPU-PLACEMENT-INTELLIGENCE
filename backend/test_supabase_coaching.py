from unittest.mock import Mock, patch

import pytest
import requests

import supabase_coaching


@patch('supabase_coaching.requests.post')
def test_uses_only_user_bearer_token_and_does_not_follow_redirects(post):
    post.return_value = Mock(status_code=200, json=lambda: [])
    assert supabase_coaching.call('https://example.supabase.co', 'publishable', 'user-token', 'coaching_list', {'p_student_id': 1}) == []
    assert post.call_args.kwargs['headers'] == {'apikey': 'publishable', 'Authorization': 'Bearer user-token'}
    assert post.call_args.kwargs['allow_redirects'] is False
    assert post.call_args.kwargs['json'] == {'p_student_id': 1}


@pytest.mark.parametrize('status,error', [(400, ValueError), (401, supabase_coaching.CoachingForbidden),
                                           (403, supabase_coaching.CoachingForbidden), (404, supabase_coaching.CoachingUnavailable),
                                           (302, supabase_coaching.CoachingUnavailable), (500, supabase_coaching.CoachingUnavailable)])
@patch('supabase_coaching.requests.post')
def test_rpc_errors_fail_closed(post, status, error):
    post.return_value = Mock(status_code=status)
    with pytest.raises(error):
        supabase_coaching.call('https://example.supabase.co', 'key', 'token', 'coaching_list', {})


@patch('supabase_coaching.requests.post', side_effect=requests.Timeout())
def test_rpc_outage_is_reported_without_response_secrets(post):
    with pytest.raises(supabase_coaching.CoachingUnavailable):
        supabase_coaching.call('https://example.supabase.co', 'key', 'token', 'coaching_create', {})


@patch('supabase_coaching.requests.post')
def test_invalid_response_shape_is_rejected(post):
    post.return_value = Mock(status_code=200, json=lambda: {'id': 1})
    with pytest.raises(supabase_coaching.CoachingUnavailable):
        supabase_coaching.call('https://example.supabase.co', 'key', 'token', 'coaching_list', {})
