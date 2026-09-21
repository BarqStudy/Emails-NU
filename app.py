import json
import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse

app = FastAPI()

# ==========================================
# 📂 إدارة البيانات
# ==========================================
def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default

# ==========================================
# 🔌 مسارات الـ API (الخلفية)
# ==========================================
@app.get("/api/colleges")
def get_colleges():
    return load_json("colleges.json", [])

@app.get("/api/doctors")
def get_doctors(
    category: str = "doctor", 
    college: str = None, 
    major: str = None, 
    search: str = None
):
    doctors_db = load_json("doctors_data.json", [])
    results = [d for d in doctors_db if d.get("category", "doctor") == category]
    
    if search:
        s = search.strip().lower()
        results = [d for d in results if s in d["name"].lower() or s in d.get("college", "").lower() or s in d.get("major", "").lower()]
    elif college:
        results = [d for d in results if d.get("college") == college]
        if major:
            results = [d for d in results if d.get("major") == major]
            
    return results

# ==========================================
# 📱 واجهة المستخدم للـ Mini App (Frontend)
# ==========================================
@app.get("/", response_class=HTMLResponse)
def serve_mini_app():
    return """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>دليل جامعة نجران</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: var(--tg-theme-bg-color, #f3f4f6); color: var(--tg-theme-text-color, #1f2937); }
    </style>
</head>
<body class="p-4 max-w-md mx-auto font-sans">

    <!-- رأس التطبيق -->
    <div class="text-center mb-6">
        <h1 class="text-xl font-bold mb-1">دليل أعضاء هيئة التدريس</h1>
        <p class="text-sm opacity-75">جامعة نجران</p>
    </div>

    <!-- أزرار التنقل الرئيسية -->
    <div class="grid grid-cols-2 gap-2 mb-4">
        <button onclick="switchTab('doctor')" id="btn-doctor" class="p-3 rounded-xl font-bold bg-blue-600 text-white shadow">أعضاء التدريس</button>
        <button onclick="switchTab('head')" id="btn-head" class="p-3 rounded-xl font-bold bg-gray-200 text-gray-700 shadow">العمداء والرؤساء</button>
    </div>

    <!-- شريط البحث -->
    <div class="mb-4">
        <input type="text" id="searchInput" oninput="handleSearch()" placeholder="🔍 ابحث باسم الدكتور أو الكلية..." 
            class="w-full p-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-black shadow-sm">
    </div>

    <!-- قائمة الكليات السريعة -->
    <div id="collegesContainer" class="mb-4 overflow-x-auto flex gap-2 pb-2 whitespace-nowrap">
        <button onclick="filterByCollege('')" class="px-3 py-1.5 rounded-full bg-gray-200 text-sm font-semibold inline-block">الكل</button>
    </div>

    <!-- نتائج البحث / القائمة -->
    <div id="resultsContainer" class="space-y-3">
        <!-- يتم تعبئتها ديناميكياً -->
    </div>

    <script>
        let tg = window.Telegram.WebApp;
        tg.expand();

        let currentCategory = 'doctor';
        let selectedCollege = '';

        async function loadColleges() {
            let res = await fetch('/api/colleges');
            let colleges = await res.json();
            let container = document.getElementById('collegesContainer');
            colleges.forEach(c => {
                let btn = document.createElement('button');
                btn.className = "px-3 py-1.5 rounded-full bg-white border border-gray-300 text-sm font-semibold inline-block shadow-sm";
                btn.innerText = c.name;
                btn.onclick = () => filterByCollege(c.name);
                container.appendChild(btn);
            });
            loadDoctors();
        }

        async function loadDoctors(search = '') {
            let url = `/api/doctors?category=${currentCategory}`;
            if (search) {
                url += `&search=${encodeURIComponent(search)}`;
            } else if (selectedCollege) {
                url += `&college=${encodeURIComponent(selectedCollege)}`;
            }
            
            let res = await fetch(url);
            let doctors = await res.json();
            renderDoctors(doctors);
        }

        function renderDoctors(doctors) {
            let container = document.getElementById('resultsContainer');
            container.innerHTML = '';
            
            if (doctors.length === 0) {
                container.innerHTML = '<div class="text-center py-10 opacity-60">لا توجد نتائج مطابقة</div>';
                return;
            }

            doctors.forEach(doc => {
                let emailsHtml = '';
                if (doc.emails && doc.emails.length > 0) {
                    emailsHtml = doc.emails.map(e => `<a href="mailto:${e.email}" class="text-blue-600 underline block text-sm font-mono mt-1">${e.email} ${e.label ? '('+e.label+')' : ''}</a>`).join('');
                } else {
                    emailsHtml = '<span class="text-sm opacity-50">لا يوجد بريد مسجل</span>';
                }

                let card = document.createElement('div');
                card.className = "bg-white p-4 rounded-xl shadow-sm border border-gray-100";
                card.innerHTML = `
                    <h3 class="font-bold text-lg text-gray-900">${doc.name}</h3>
                    <p class="text-sm text-gray-600">الكلية: ${doc.college || 'غير محدد'}</p>
                    ${doc.major ? `<p class="text-sm text-gray-600">التخصص: ${doc.major}</p>` : ''}
                    <p class="text-sm text-gray-600">الرتبة: ${doc.rank || 'غير محدد'}</p>
                    <div class="mt-2 pt-2 border-t border-gray-100">${emailsHtml}</div>
                `;
                container.appendChild(card);
            });
        }

        function switchTab(cat) {
            currentCategory = cat;
            selectedCollege = '';
            document.getElementById('btn-doctor').className = cat === 'doctor' ? "p-3 rounded-xl font-bold bg-blue-600 text-white shadow" : "p-3 rounded-xl font-bold bg-gray-200 text-gray-700 shadow";
            document.getElementById('btn-head').className = cat === 'head' ? "p-3 rounded-xl font-bold bg-blue-600 text-white shadow" : "p-3 rounded-xl font-bold bg-gray-200 text-gray-700 shadow";
            loadDoctors();
        }

        function filterByCollege(collegeName) {
            selectedCollege = collegeName;
            document.getElementById('searchInput').value = '';
            loadDoctors();
        }

        function handleSearch() {
            let query = document.getElementById('searchInput').value;
            if (query.length > 0) {
                selectedCollege = '';
            }
            loadDoctors(query);
        }

        loadColleges();
    </script>
</body>
</html>
    """
