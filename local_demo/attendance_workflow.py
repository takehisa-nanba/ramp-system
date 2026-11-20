"""Exercise the worker's timecard and the manager's approval in separate sessions."""
from datetime import date, datetime, time, timedelta
from playwright.sync_api import expect


def check_attendance(browser, after_restart):
    page = browser.new_page(base_url="http://127.0.0.1:8080", timezone_id="Asia/Tokyo")
    stamp_reason = "初回打刻の出勤時刻を訂正"
    leave_reason = "予定日の有給休暇を取得"
    def login(code):
        page.context.clear_cookies()
        page.goto("/")
        page.locator('input[type=text]').fill(code)
        page.locator('input[type=password]').fill("RampDemo-Local1")
        page.locator('form button[type=submit]').click()
        expect(page.get_by_role("heading", name="ホーム", exact=True)).to_be_visible()
        page.goto("/attendance")
    def button(name):
        return page.get_by_role("button", name=name, exact=True)
    def row(reason):
        return page.get_by_role("listitem").filter(has_text=reason)
    def records(day):
        result = page.request.get("/api/attendance/timecards", params={"date": day})
        assert result.ok, result.status
        return result.json()

    login("demo-worker")
    if not after_restart:
        page.get_by_label("勤務するサービス").select_option(index=1)
        button("出勤する").click()
        expect(button("退勤する")).to_be_enabled()
        page.goto("/dashboard")
        page.get_by_label("活動種別").select_option(label="事務作業（記録・書類作成）")
        button("計測を開始").click()
        page.reload()
        button("終了して記録").click()
        expect(page.get_by_role("list", name="本日の活動")).to_contain_text("事務作業（記録・書類作成）")
        page.get_by_label("活動種別").select_option(label="個別支援・面談")
        page.get_by_label("対象利用者").select_option(label="サンプル 移行")
        button("計測を開始").click()
        page.get_by_label("活動メモ").fill("支援計画に沿って振り返り")
        button("終了して記録").click()
        expect(page.get_by_role("list", name="本日の活動")).to_contain_text("支援計画に沿って振り返り")
        page.goto("/attendance")
        button("退勤する").click()
        page.get_by_role("dialog").get_by_role("button", name="退勤する").click()
        expect(page.get_by_role("dialog")).to_be_hidden()
        expect(button("退勤する")).to_be_disabled()
        button("新規修正申請を作成する").click()
        day = page.get_by_label("対象日").input_value()
        card, = records(day)
        start = datetime.fromisoformat(card["check_in"])
        earlier = max(start - timedelta(minutes=5), datetime.combine(start.date(), time.min, start.tzinfo))
        page.get_by_label("修正後の時刻").fill(earlier.strftime("%H:%M"))
        page.get_by_label("申請理由").fill(stamp_reason)
        button("申請を送信").click()
        expect(row(stamp_reason)).to_contain_text("確認待ち")

        next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
        button("新規修正申請を作成する").click()
        page.get_by_label("対象日").fill(next_day)
        page.get_by_label("申請種別").select_option("PAID_LEAVE")
        page.get_by_label("申請理由").fill(leave_reason)
        button("申請を送信").click()
        expect(row(leave_reason)).to_contain_text("確認待ち")
        worker_id = page.request.get("/api/dashboard/staff/status").json()["current_staff_id"]
        login("demo-staff")
        # Use the regular shift API to provide the required scheduled day for leave.
        csrf = next(c["value"] for c in page.context.cookies() if c["name"] == "csrf_access_token")
        shift = page.request.post("/api/attendance/shifts", headers={"X-CSRF-TOKEN": csrf},
            data=dict(supporter_id=worker_id, target_date=next_day, start_time="09:00", end_time="18:00", break_minutes=60))
        assert shift.status == 201, shift.text()
        for reason in (stamp_reason, leave_reason):
            row(reason).get_by_role("button", name="承認して反映").click()
            expect(row(reason)).to_contain_text("承認済み")
        login("demo-worker")

    for reason in (stamp_reason, leave_reason):
        expect(row(reason)).to_contain_text("承認済み")
    items = page.request.get("/api/attendance/requests").json()
    correction = next(item for item in items if item["request_reason"] == stamp_reason)
    absence = next(item for item in items if item["request_reason"] == leave_reason)
    card, = records(correction["target_date"])
    assert card["check_out"] and datetime.fromisoformat(card["check_in"]).strftime("%H:%M:%S") == correction["requested_time"] + ":00"
    leave, = records(absence["target_date"])
    assert leave["absence_type"] == "PAID_LEAVE" and leave["deemed_work_minutes"] == 480
    page.close()
