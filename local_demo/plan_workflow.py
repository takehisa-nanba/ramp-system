"""Use distinct staff, manager and participant sessions on the local demo."""
from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse
from calendar_input import set_calendar_date
from playwright.sync_api import expect


def check_plan_cycle(browser, after_restart=False):
    page = browser.new_page(base_url="http://127.0.0.1:8080", timezone_id="Asia/Tokyo")
    page.set_default_timeout(10000)
    def button(name):
        return page.get_by_role("button", name=name, exact=True)

    def login(code, participant=False):
        page.context.clear_cookies()
        page.goto("/")
        if participant:
            button("利用者ログイン").click()
        page.locator('input[type="text"]').fill(code)
        page.locator('input[type="password"]').fill("RampDemo-Local1")
        page.locator('form button[type="submit"]').click()
        expect(page.get_by_role("heading", name="マイページ" if participant else "ホーム", exact=True)).to_be_visible()

    def open_plan():
        page.goto("/job-retention")
        page.get_by_role("link", name="サンプル 定着").click()
        page.get_by_role("link", name="定着支援の個別支援計画").click()
        expect(page.get_by_role("heading", name="個別支援計画ステータス")).to_be_visible()

    def interview(content):
        button("面談を記録する").click()
        page.get_by_label("本人の希望と面談で確認した内容").fill(content)
        button("面談を保存").click()
        expect(page.get_by_text("原案作成に使用できます", exact=False).first).to_be_visible()

    login("demo-worker")
    open_plan()
    if after_restart:
        expect(page.get_by_text("就労先での休憩方法を振り返った", exact=True)).to_be_visible()
        expect(button("原案を編集")).to_be_visible()
        page.close()
        return
    expect(button("新規計画作成")).to_be_disabled()
    interview("午後の疲れに合わせて休憩を相談したい")
    button("新規計画作成").click()
    # End within a month so the same workflow also verifies the review alert.
    dates = page.locator('form input[aria-haspopup="dialog"]')
    start = date.fromisoformat(dates.first.input_value())
    set_calendar_date(page, dates.nth(1), (start + timedelta(days=20)).isoformat())
    page.get_by_placeholder("例：就労に向けた意欲", exact=False).fill("午後の集中を維持したい")
    page.get_by_placeholder("例：毎日休まず", exact=False).fill("休憩を相談しながら働く")
    page.get_by_placeholder("例：作業開始時", exact=False).fill("疲れたときに声をかける")
    page.get_by_placeholder("例：手順書を", exact=False).fill("休憩の時間を確認する")
    button("原案を作成して目標保存").click()
    editor = page.locator("section").filter(has=page.get_by_role("heading", name="就労定着支援計画の詳細")).last
    editor.get_by_label("就職記録（承認前に必須）").select_option(index=1)
    def save_details():
        with page.expect_response(lambda r: r.request.method == "PUT" and r.url.endswith("/retention-detail")) as response:
            button("計画詳細を保存").click()
        assert response.value.ok
    save_details()
    button("職場・労働条件").click()
    editor.get_by_label("業務内容（承認前に必須）").fill("書類整理")
    save_details()
    button("本人・生活情報").click()
    editor.get_by_label("利用目標・本人ニーズ（承認前に必須）").fill("働き続けたい")
    save_details()
    button("支援内容").click()
    editor.get_by_label("支援方針・内容", exact=False).fill("本人と休憩方法を相談")
    editor.get_by_label("頻度", exact=False).fill("月1回")
    button("支援項目を追加").click()
    expect(button("この支援項目を保存")).to_be_visible()
    button("本人同席会議を記録").click()
    page.get_by_placeholder("例：就労に向けた体調管理", exact=False).fill("休憩のとり方")
    page.get_by_placeholder("例：就寝・起床時間", exact=False).fill("本人と相談して休憩を決める")
    button("会議を記録する").click()
    expect(page.get_by_text("本人同席会議完了", exact=True)).to_be_visible()
    expect(button("計画を承認（成案化）する")).to_have_count(0)
    login("demo-staff")
    open_plan()
    button("計画を承認（成案化）する").click()
    button("承認する").click()
    expect(page.get_by_text("説明・同意待ち", exact=True).first).to_be_visible()
    login("demo-retention", participant=True)
    expect(page.get_by_text("休憩の時間を確認する", exact=True)).to_be_visible()
    expect(page.get_by_text("本人と休憩方法を相談", exact=True)).to_be_visible()
    page.get_by_role("checkbox").check()
    button("同意を記録する").click()
    expect(page.get_by_text("第1版　有効", exact=True)).to_be_visible()
    login("demo-worker")
    page.goto("/action-items")
    page.get_by_role("heading", name="個別支援計画の見直し時期です", exact=False).click()
    expect(page.get_by_role("heading", name="個別支援計画ステータス")).to_be_visible()
    assert parse_qs(urlparse(page.url).query).get("office_service_configuration_id")
    button("新規実施").click()
    page.get_by_placeholder("例：第2期計画", exact=False).fill("就労先での休憩方法を振り返った")
    button("モニタリングを登録").click()
    expect(page.get_by_text("就労先での休憩方法を振り返った", exact=True)).to_be_visible()
    expect(button("次期原案を作成")).to_be_disabled()
    interview("再面談で休憩後の働き方を確認した")
    button("次期原案を作成").click()
    button("次期原案を作成する").click()
    expect(button("原案を編集")).to_be_visible()
    page.close()
