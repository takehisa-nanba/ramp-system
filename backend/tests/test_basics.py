def test_app_exists(app):
    """アプリケーションが虚無ではないことを確認"""
    assert app is not None

def test_app_is_testing(app):
    """テストモードで起動していることを確認"""
    assert app.config['TESTING'] is True