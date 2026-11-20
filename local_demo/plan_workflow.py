"""Use distinct staff, manager and participant sessions on the local demo."""
from datetime import timedelta
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
    from datetime import date
    dates = page.locator('form input[type=date]')
    start = date.fromisoformat(dates.first.input_value())
    dates.nth(1).fill((start + timedelta(days=20)).isoformat())
    page.get_by_placeholder("例：就労に向けた意欲", exact=False).fill("午後の集中を維持したい")
    page.get_by_placeholder("例：毎日休まず", exact=False).fill("休憩を相談しながら働く")
    page.get_by_placeholder("例：作業開始時", exact=False).fill("疲れたときに声をかける")
    page.get_by_placeholder("例：手順書を", exact=False).fill("休憩の時間を確認する")
    button("原案を作成して目標保存").click()
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
    page.get_by_role("checkbox").check()
    button("同意を記録する").click()
    expect(page.get_by_text("第1版　有効", exact=True)).to_be_visible()
    login("demo-worker")
    open_plan()
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
