import pytest

def test_resolve_tenant_scope(app):
    """role_scopesによるアクセス制御検証"""
    from backend.app.utils.tenant import resolve_tenant_scope
    from backend.app.domain.attendance.exceptions import AttendanceForbiddenError
    from unittest.mock import patch, MagicMock
    import pytest

    with app.app_context():
        supporter_id = 1

        with patch('backend.app.extensions.db.session.get') as mock_get:
            mock_supporter = MagicMock()
            mock_supporter.office_id = 100

            mock_office = MagicMock()
            mock_office.corporation_id = 200

            def side_effect(model, id):
                if model.__name__ == 'Supporter':
                    return mock_supporter
                if model.__name__ == 'OfficeSetting':
                    return mock_office
                return None

            mock_get.side_effect = side_effect

            # CORPORATE
            scope = resolve_tenant_scope(supporter_id, ['CORPORATE'])
            assert scope['level'] == 'CORPORATE'
            assert scope['corp_id'] == 200
            assert not scope['self_only']

            # SYSTEM + CORPORATE (CORPORATE takes precedence)
            scope = resolve_tenant_scope(supporter_id, ['SYSTEM', 'CORPORATE'])
            assert scope['level'] == 'CORPORATE'
            assert scope['corp_id'] == 200
            assert not scope['self_only']

            # SYSTEM
            scope = resolve_tenant_scope(supporter_id, ['SYSTEM'])
            assert scope['level'] == 'SYSTEM_SELF'
            assert scope['self_only']

            # JOB
            scope = resolve_tenant_scope(supporter_id, ['JOB'])
            assert scope['level'] == 'JOB_SELF'
            assert scope['self_only']

            # STAFF
            scope = resolve_tenant_scope(supporter_id, [])
            assert scope['level'] == 'STAFF'
            assert scope['self_only']

            # CORPORATE missing office_id
            mock_supporter.office_id = None
            with pytest.raises(AttendanceForbiddenError):
                resolve_tenant_scope(supporter_id, ['CORPORATE'])

            # CORPORATE missing corporation_id
            mock_supporter.office_id = 100
            mock_office.corporation_id = None
            with pytest.raises(AttendanceForbiddenError):
                resolve_tenant_scope(supporter_id, ['CORPORATE'])

def test_extract_staff_id_strict():
    """extract_staff_idの厳密なバリデーション検証"""
    from backend.app.utils.tenant import extract_staff_id
    from backend.app.domain.attendance.exceptions import AttendanceForbiddenError

    # Valid
    assert extract_staff_id('staff:1') == 1
    assert extract_staff_id('staff:123') == 123

    invalid_cases = [
        None,
        1,
        '',
        'staff:',
        'staff:abc',
        'staff:-1',
        'staff:+1',
        'staff:1:extra',
        'user:1',
        'staff:０１',
        'staff:１２３',
        'staff:01',
        'staff:0'
    ]

    for case in invalid_cases:
        with pytest.raises(AttendanceForbiddenError):
            extract_staff_id(case)
