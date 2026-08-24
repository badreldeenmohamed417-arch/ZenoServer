import json
from google import genai
from google.genai import types

from rag.rag_runtime.core.config import settings

# 1. إعداد الـ API Client (الطريقة المحدثة)
client = genai.Client(api_key=settings.gemini_api_key)

def get_data():
    with open('subjects.json') as f:
        subjects_data = json.load(f)
    return subjects_data

subjects_data = get_data()

def determine_subject(student_grade_id, student_question):
    """
    تحديد المادة باستخدام أحدث مكتبة genai
    """
    grade_data = subjects_data["subjects"].get(student_grade_id)
    if not grade_data:
        return "الصف الدراسي غير موجود"

    available_subjects = grade_data["subjects"]

    prompt = f"""
    أنت خبير تصنيف تعليمي. مهمتك تحديد مادة السؤال من القائمة التالية للصف: {grade_data['name']}.
    القائمة المتاحة: {json.dumps(available_subjects, ensure_ascii=False)}
    السؤال: "{student_question}"

    الهدف: حدد الـ "id" للمادة المناسبة.
    """

    print(prompt)
    # 3. استخدام generate_content مع إجبار النموذج على مخرجات JSON
    # لاحظ استخدام 'gemini-2.0-flash' (بدلاً من 3.5-flash-lite غير الموجود حالياً)
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            # تحديد الـ Schema لضمان دقة المخرجات
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "subject_id": {"type": "STRING"}
                },
                "required": ["subject_id"]
            }
        )
    )

    # 4. معالجة النتيجة (بما أننا حددنا الـ MIME type كـ JSON، فالنتيجة جاهزة للـ parse)
    try:
        result = json.loads(response.text)
        return result.get("subject_id")
    except Exception as e:
        return f"خطأ في التصنيف: {e}"


# --- تجربة الاختبار ---
grade = "grade_2_secondary_science"
question = "إيه الفرق بين الروابط الأيونية والتساهمية في الذرة؟"

subject_id = determine_subject(grade, question)
print(f"🎯 المادة المكتشفة للنظام: {subject_id}")