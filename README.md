# ATLAS Work Control Agent v0.1

نمونه اولیه قطعی و فقط‌خواندنی برای کنترل دیتابیس `ATLAS-WORK`.

## تصمیم معماری

نسخه 0.1 برای اجرای قواعد کنترلی به مدل زبانی نیاز ندارد. بنابراین:

- `OPENAI_API_KEY` در این مرحله لازم نیست.
- قواعد WIP، مالک، اقدام بعدی، پیش‌نیاز، ریسک فراموشی و عدم تغییر به‌صورت قطعی اجرا می‌شوند.
- اتصال زنده فقط به `NOTION_TOKEN` و `NOTION_DATA_SOURCE_ID` نیاز دارد.
- OpenAI بعداً فقط برای تشخیص معنایی پیشرفته، خوشه‌بندی مشابهت و خلاصه‌سازی طبیعی اضافه می‌شود.

## قابلیت‌ها

- کنترل سقف WIP
- تشخیص رکورد Active بدون مالک
- تشخیص اقدام بعدی خالی یا مبهم
- تشخیص ریسک فراموشی
- پیشنهاد خوشه‌های دوباره‌کاری بدون ادغام خودکار
- کنترل پیش‌نیاز فعال‌سازی
- تولید Focus Brief
- تولید Run Log
- تضمین Read-only در سطح برنامه

## اجرای آفلاین

```bash
python -m atlas_work_control.cli --fixture fixtures/atlas_work_sample.json
```

## اجرای زنده با Notion

```bash
export NOTION_TOKEN="..."
export NOTION_DATA_SOURCE_ID="c92d50eb-e0dd-4edb-a3e5-586e81ce7304"
python -m atlas_work_control.cli --notion
```

توکن نباید داخل کد، Notion، پیام یا Git ثبت شود.

## اجرای تست‌ها

```bash
python -m pytest
```

معیار پذیرش:

- تمام تست‌های Critical باید Pass شوند.
- هیچ رکورد ATLAS-WORK تغییر نکند.
- هر هشدار دارای کد قاعده، شدت، کد فعالیت و دلیل باشد.
