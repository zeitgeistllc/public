import streamlit as st
import time
import requests

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="מערכת לבדיקת שוכרים",
    layout="wide",  # Increased width for better layout
    initial_sidebar_state="collapsed"
)

# --- RTL STYLES ---
# This CSS block forces a right-to-left layout for the entire application,
# which is necessary for proper Hebrew text alignment.
st.markdown("""
    <style>
        body, .main {
            direction: rtl !important;
        }
        /* Ensure all text within the main content area is right-aligned */
        .main * {
            text-align: right !important;
        }
        /* Keep number input text left-aligned for standard number entry */
        input[type="number"] {
            text-align: left !important;
        }
        /* Keep placeholder text aligned with the input's direction */
        input::placeholder {
            text-align: right !important;
        }
    </style>
""", unsafe_allow_html=True)


# --- AGENTS (No changes needed here) ---
class VerificationAgent:
    """
    Agent to verify an applicant's ID number against the Bank of Israel's public records.
    This uses the live, production API.
    """
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })

    def run(self, id_number: str) -> dict:
        """
        Runs the verification check for a single ID number.
        """
        if not id_number or not id_number.isdigit():
            return {"id_check": {"status": "לא הוזן מספר ת.ז."}}

        try:
            id_url = f"https://mugbalim.boi.org.il/api/umbraco/api/IframeSearchById/he/{id_number}"
            res = self.session.get(id_url, timeout=10)
            res.raise_for_status()
            response_data = res.json()

            if response_data.get("isRestricted") is False:
                return {"id_check": {"status": "✅ תקין"}}
            else:
                return {"id_check": {"status": "❌ נמצאה הגבלה"}}
        except requests.exceptions.RequestException as e:
            return {"id_check": {"status": f"⚠️ שגיאת תקשורת: {e}"}}
        except Exception as e:
            return {"id_check": {"status": f"⚠️ שגיאה לא צפויה: {e}"}}

class FinancialRiskAgent:
    """
    Agent to assess the financial risk based on combined income and expenses.
    """
    def run(self, salaries: list, user_inputs: dict) -> dict:
        total_income = sum(float(s or 0) for s in salaries)
        if total_income == 0:
            return {"risk_level": "חסר מידע", "reasoning": "יש להזין הכנסה של מועמד אחד לפחות"}

        rent = float(user_inputs.get("rent", 0))
        arnona = float(user_inputs.get("arnona", 0))
        living_costs = float(user_inputs.get("living_costs", 0))

        housing_cost = rent + arnona
        total_expenses = housing_cost + living_costs
        expense_ratio = total_expenses / total_income if total_income > 0 else float('inf')

        risk_level = "נמוכה"
        if expense_ratio > 0.65:
            risk_level = "גבוהה מאוד"
        elif expense_ratio > 0.50:
            risk_level = "גבוהה"
        elif expense_ratio > 0.40:
            risk_level = "בינונית"

        return {
            "total_monthly_income": f"₪{total_income:,.2f}",
            "total_housing_cost": f"₪{housing_cost:,.2f}",
            "user_defined_living_cost": f"₪{living_costs:,.2f}",
            "total_estimated_expenses": f"₪{total_expenses:,.2f}",
            "expense_to_income_ratio": f"{expense_ratio:.2%}",
            "risk_level": risk_level,
            "reasoning": f"יחס ההוצאות המשולב להכנסה עומד על {expense_ratio:.2%}."
        }

# --- STREAMLIT UI ---
st.markdown("<h1 style='text-align: center; direction: rtl;'>🏠 מערכת לבדיקת שוכרים</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray; direction: rtl;'>מערכת מקיפה לניתוח כדאיות של שוכרים משותפים.</p>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- Main Columns for Input ---
main_cols = st.columns(2)

with main_cols[0]:
    with st.expander("📝 עלויות משק בית (ש\"ח)", expanded=True):
        rent = st.number_input("שכירות חודשית", min_value=0, value=6000, step=100)
        arnona = st.number_input("ארנונה", min_value=0, value=1000, step=100)
        living_costs = st.number_input(
            "עלויות מחיה",
            min_value=0,
            value=5000,
            step=100,
            help='הערכה ריאלית להוצאות חודשיות (לא כולל שכירות וארנונה). כלול כאן: מזון, חשבונות, תחבורה, ילדים, וכו\'. למשפחה, סכום זה הוא לרוב מעל 10,000 ש"ח.'
        )

with main_cols[1]:
    with st.expander("ℹ️ **הערכת עלויות מחיה חודשיות (ללא שכירות וארנונה)**", expanded=True):
        # The div with explicit rtl/right-align is kept for robustness
        st.markdown("""
        <div style="direction: rtl; text-align: right;">
        השתמשו בטבלה זו כדי להזין הערכה מציאותית יותר בשדה <b>עלויות מחיה</b>. אנשים נוטים להעריך את הוצאותיהם בחסר.
        </div>
        """, unsafe_allow_html=True)
        # FIXED: Changed the markdown table alignment syntax to right-align all columns.
        st.markdown("""
| גודל משק הבית | אורח חיים חסכוני | אורח חיים ממוצע / נוח |
| ---: | ---: | ---: |
| **אדם יחיד** | ₪3,500 - ₪4,500 | ₪5,000 - ₪7,000+ |
| **זוג** | ₪5,500 - ₪7,000 | ₪8,000 - ₪11,000+ |
| **זוג + ילד** | ₪8,000 - ₪10,000 | ₪11,000 - ₪15,000+ |
| **זוג + 2 ילדים**| ₪10,000 - ₪13,000 | ₪14,000 - ₪20,000+ |
        """)

with st.expander("👥 מועמדים", expanded=True):
    if "num_applicants" not in st.session_state:
        st.session_state.num_applicants = 1

    # MODIFIED: Placed an empty column first to push the buttons to the right.
    _, c2, c1 = st.columns([0.6, 0.2, 0.2])
    if c1.button("➕ הוסף מועמד/ת"):
        st.session_state.num_applicants += 1
    if c2.button("➖ הסר מועמד/ת") and st.session_state.num_applicants > 1:
        st.session_state.num_applicants -= 1

    applicants = []
    applicant_cols = st.columns(st.session_state.num_applicants)

    for i, col in enumerate(applicant_cols):
        with col:
            st.markdown(f"**מועמד/ת #{i+1}**")
            # REMOVED: Name input field is no longer here.
            id_number = st.text_input("מספר תעודת זהות", key=f"id_{i}", placeholder="לדוגמה: 123456789")
            salary = st.number_input(
                "שכר נטו חודשי (ש\"ח)",
                min_value=0,
                value=12000,
                step=100,
                key=f"salary_{i}",
                help="הכנס שכר נטו לאחר מיסים"
            )
            # REMOVED: 'name' is no longer added to the dictionary.
            applicants.append({
                "id_number": id_number.strip(),
                "salary": salary
            })

if st.button("🚀 בצע ניתוח", type="primary", use_container_width=True):
    # --- ANALYSIS LOGIC ---
    verify_agent = VerificationAgent()
    risk_agent = FinancialRiskAgent()
    report_applicants = []
    all_salaries = []

    with st.spinner("...מבצע בדיקה מול בנק ישראל ומנתח נתונים"):
        for app in applicants:
            all_salaries.append(app["salary"])
            verification_results = verify_agent.run(app["id_number"])
            # REMOVED: 'name' is no longer added to the report dictionary.
            report_applicants.append({
                "id_number": app["id_number"],
                "salary": f"₪{float(app['salary']):,.2f}",
                "verification": verification_results
            })

        financial_report = risk_agent.run(
            all_salaries,
            {"rent": rent, "arnona": arnona, "living_costs": living_costs}
        )
    st.success("✅ הניתוח הושלם")
    st.markdown("---")

    # --- RESULTS SECTION ---
    st.subheader("📄 תוצאות הניתוח")
    res_cols = st.columns([2, 3]) 

    with res_cols[0]:
        st.markdown("**📋 דוחות מועמדים**")
        # MODIFIED: Use enumerate to get an index for each applicant.
        for i, r in enumerate(report_applicants):
            with st.container(border=True):
                # REMOVED: Name display logic is gone.
                id_display = r['id_number'] if r['id_number'] else "לא הוזן"
                # MODIFIED: Display applicant number instead of name.
                st.markdown(f"**👤 מועמד/ת #{i+1}** (ת.ז. `{id_display}`)")
                st.metric("שכר נטו", r["salary"])
                st.markdown(f"**בדיקת הגבלה בבנק ישראל:** {r['verification']['id_check']['status']}")


    with res_cols[1]:
        st.markdown("**📊 ניתוח פינסי משותף**")
        with st.container(border=True):
            fin_cols1 = st.columns(3)
            fin_cols1[0].metric("סה\"כ הכנסה", financial_report["total_monthly_income"])
            fin_cols1[1].metric("סה\"כ עלויות דיור", financial_report["total_housing_cost"])
            fin_cols1[2].metric("עלויות מחיה", financial_report["user_defined_living_cost"])

            fin_cols2 = st.columns(2)
            fin_cols2[0].metric("סה\"כ הוצאות", financial_report["total_estimated_expenses"])
            fin_cols2[1].metric("יחס הוצאות להכנסה", financial_report["expense_to_income_ratio"])

            risk_colors = {
                "נמוכה": "🟢", "בינונית": "🟠", "גבוהה": "🔴",
                "גבוהה מאוד": "🚨", "חסר מידע": "⚪"
            }
            risk_icon = risk_colors.get(financial_report["risk_level"], "")
            risk_display = f"{risk_icon} {financial_report['risk_level'].upper()}"

            st.markdown("---")
            st.markdown(
                f"<div style='text-align: center; direction: rtl;'>"
                f"<h3>רמת סיכון: <span style='font-size: 1.2em;'>{risk_display}</span></h3>"
                f"<p>💡 <i>{financial_report['reasoning']}</i></p>"
                f"</div>",
                unsafe_allow_html=True
            )
    st.markdown("---")

# --- LEGAL & INFORMATIONAL SECTION ---
with st.expander("⚠️ אודות, פרטיות ותנאי שימוש", expanded=False):
    # FIXED: The outer <div> tag was removed from the markdown string to prevent rendering conflicts.
    st.markdown("""
<h4>כתב ויתור פיננסי וייעוץ</h4>
<p>
    מערכת זו מספקת ניתוח אינפורמטיבי כללי בלבד ואינה מהווה ייעוץ פיננסי, משפטי או מקצועי. כל התוצאות הן הערכות המבוססות על נתונים זמינים לציבור ועל קלט המשתמש, וייתכן שאינן משקפות סיכונים מהחיים האמיתיים או תוצאות בפועל. המשתמשים אינם רשאים להסתמך אך ורק על המערכת לצורך קבלת החלטות מהותיות.
</p>

<h4>היעדר אחריות והגבלת חבות</h4>
<p>
    האתר, בעליו ומפתחין אינם מספקים כל אחריות או ערובה לגבי הדיוק, השלמות או המהימנות של הניתוח. התוצאות אינן מבטיחות תוצאות עתידיות, וביצועי עבר או ניתוחי עבר אינם יכולים לחזות סיכונים עתידיים. הפלטפורמה לא תהיה אחראית לכל נזק ישיר, עקיף, מקרי או תוצאתי הנובע מהשימוש או חוסר היכולת להשתמש במערכת, מהחלטות שהתקבלו או משגיאות בהזנת נתונים.
</p>

<h4>אחריות המשתמש והסכמה</h4>
<p>
    המשתמשים נושאים באחריות המלאה להבטיח שכל מידע אישי המוזן למערכת מעובד כדין ובהסכמה מפורשת של נושאי המידע. המפעיל לא יהיה אחראי לכל שימוש לרעה, שימוש בלתי מורשה או הזנת נתונים ללא הסכמה, לרבות כל תביעה או תלונה מצד נושאי המידע.
</p>

<h4>סעיף שיפוי</h4>
<p>
    המשתמשים מסכימים לשפות, להגן על, ולשמור על מפעילי האתר, המארחים, המפתחים והשותפים מפני כל וכל תביעה, דרישה, הפסד, חבות או הוצאה (כולל שכר טרחת עורכי דין) מצד שלישי הנובעים מ:
</p>
<ul>
    <li>השימוש, שימוש לרעה, או חוסר היכולת להשתמש במערכת;</li>
    <li>כל תביעה הקשורה לנתונים שנמסרו ללא הסכמה נאותה;</li>
    <li>כל הסתמכות על הניתוח או ההמלצות שסופקו;</li>
    <li>כל הפרה לכאורה של חוק, הפרת זכויות או פגיעה בזכויות עקב הקלט או פלט המערכת.</li>
</ul>

<h4>כתב ויתור על נתונים ושירותים של צד שלישי</h4>
<p>
    המערכת משתמשת בשירותים חיצוניים (למשל, ה-API של בנק ישראל) לצורך אימות וניתוח. המפעיל אינו אחראי לעיכובים, שגיאות או נזקים הנובעים מכשלים, הפרעות או שינויי מדיניות של שירותי צד שלישי.
</p>

<h4>הצהרת פרטיות/הגנת נתונים</h4>
<p>
    המערכת אינה מאחסנת, מתעדת או אוספת נתונים אישיים מעבר לחיבור הפעיל של המשתמש, ומוחקת את כל נתוני החיבור לאחר יציאה או רענון. מומלץ למשתמשים לא להזין נתונים אישיים שאינם נחוצים ולהבטיח ציות לתקנות הגנת הנתונים (GDPR וחוקים מקומיים).
</p>
""", unsafe_allow_html=True)

# --- SHORT DISCLAIMER & Footer ---
st.markdown(
    """
    <div style='text-align: center; color: #888; font-size: 0.9em; margin-top: 20px; direction: rtl;'>
        השימוש במערכת כפוף לתנאי השימוש ומדיניות הפרטיות המפורטים באזור "אודות, פרטיות ותנאי שימוש" לעיל.
    </div>
    <br>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style='text-align: center; color: #bbb; margin-top: 20px; direction: rtl;'>
        מערכת לבדיקת שוכרים © 2025
    </div>
    """,
    unsafe_allow_html=True
)