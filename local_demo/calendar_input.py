def set_calendar_date(page, field, value):
    field.click()
    dialog = page.get_by_role("dialog").last
    dialog.get_by_role("button", name="直接入力に切り替え").click()
    for label, part in zip(("年", "月", "日"), value.split("-")):
        dialog.get_by_role("textbox", name=label, exact=True).fill(part)
    dialog.get_by_role("button", name="確定", exact=True).click()
