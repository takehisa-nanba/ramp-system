"""Exercise the published SPA and authenticated API through localhost."""
import sys
from playwright.sync_api import sync_playwright, expect


def check(browser, after_restart):
    page = browser.new_page(base_url="http://127.0.0.1:8080")
    page.set_default_timeout(15000)
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))

    def login(account, user=False):
        page.goto("/")
        if user:
            page.get_by_role("button", name="利用者ログイン").click()
        page.locator('input[type="text"]').fill(account)
        page.locator('input[type="password"]').fill("RampDemo-Local1")
        page.locator('form button[type="submit"]').click()

    login("demo-user", user=True)
    expect(page.get_by_role("heading", name="マイページ", exact=True)).to_be_visible()
    note = "ローカル動作確認で入力した日報"
    if not after_restart:
        page.get_by_role("button", name="通所する").click()
        expect(page.get_by_role("button", name="退所する")).to_be_enabled()
        page.locator("textarea").fill(note)
        page.get_by_role("button", name="日報を保存する").click()
        expect(page.get_by_role("button", name="日報を修正する")).to_be_visible()
        page.get_by_role("checkbox").check()
        page.get_by_role("button", name="同意を記録する").click()
        expect(page.get_by_text("第1版　有効")).to_be_visible()
    page.reload()
    expect(page.locator("textarea")).to_have_value(note)
    expect(page.get_by_role("button", name="退所する")).to_be_enabled()
    expect(page.get_by_text("第1版　有効")).to_be_visible()
    page.get_by_role("button", name="ログアウト").click()
    expect(page.get_by_role("button", name="職員ログイン")).to_be_visible()
    login("demo-staff")
    expect(page.get_by_role("heading", name="ホーム", exact=True)).to_be_visible()
    page.goto("/job-retention")
    page.get_by_role("link", name="サンプル 定着").click()
    expect(page.get_by_role("heading", name="就労定着支援の契約と記録")).to_be_visible()
    if not after_restart:
        page.get_by_role("button", name="支援を記録する").click()
        page.locator('[name="minutes"]').fill("20")
        page.locator('[name="content"]').fill("就労先での状況を本人と確認した")
        page.get_by_role("button", name="記録を保存").click()
    expect(page.get_by_text("就労先での状況を本人と確認した")).to_be_visible()
    page.get_by_role("link", name="定着支援の個別支援計画").click()
    expect(page.get_by_role("heading", name="個別支援計画ステータス")).to_be_visible()
    assert not errors, errors
    page.close()


if __name__ == "__main__":
    from plan_workflow import check_plan_cycle

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        check(browser, "--after-restart" in sys.argv)
        check_plan_cycle(browser, "--after-restart" in sys.argv)
        browser.close()
