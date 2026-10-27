import os
import re
import json
import subprocess
import urllib.parse
import requests

# กำหนด Path ของโฟลเดอร์โจทย์
solutions_path = "solutions/problems"
if not os.path.exists(solutions_path):
    solutions_path = "solutions"

folders = [d for d in os.listdir(solutions_path) if os.path.isdir(os.path.join(solutions_path, d))]

print(f"พบโฟลเดอร์โจทย์ทั้งหมด {len(folders)} ข้อ กำลังดึงข้อมูลจาก LeetCode API...")

# ดึงข้อมูลปัญหาทั้งหมดจาก LeetCode API
url = "https://leetcode.com/api/problems/algorithms/"
response = requests.get(url)
data = response.json()

def normalize_key(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

# ดึงข้อมูล Topics / Tags
print("กำลังดึงข้อมูล Topics / Tags...")
tags_dataset_url = "https://raw.githubusercontent.com/WilliamZhang20/leetcode-clusters/master/data/problems.json"
tags_map = {}
try:
    tags_resp = requests.get(tags_dataset_url, timeout=15)
    if tags_resp.status_code == 200:
        clusters_data = tags_resp.json()
        tag_name_lookup = {t['slug']: t['name'] for t in clusters_data.get('tags', [])}
        for p in clusters_data.get('problems', []):
            p_tags = [tag_name_lookup.get(t, t.title()) for t in p.get('tags', [])]
            tags_map[p['slug']] = p_tags
            tags_map[normalize_key(p['slug'])] = p_tags
            tags_map[normalize_key(p['title'])] = p_tags
except Exception as e:
    print(f"คำเตือน: ไม่สามารถดึง tags dataset ได้ ({e})")

def fetch_tags_fallback(slug):
    try:
        query = 'query { question(titleSlug: "%s") { topicTags { name } } }' % slug
        cmd = [
            'curl', '-s', '-X', 'POST', 'https://leetcode.com/graphql',
            '-H', 'Content-Type: application/json',
            '-H', 'Referer: https://leetcode.com',
            '-H', 'Origin: https://leetcode.com',
            '-H', 'User-Agent: Mozilla/5.0',
            '-d', json.dumps({'query': query})
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        qdata = json.loads(res.stdout)
        return [t['name'] for t in qdata.get('data', {}).get('question', {}).get('topicTags', [])]
    except Exception:
        return []

# สร้าง Map จับคู่ด้วย title_slug และ title
problem_map = {}
for p in data['stat_status_pairs']:
    title_slug = p['stat']['question__title_slug']
    question_id = int(p['stat']['frontend_question_id'])
    title = p['stat']['question__title'].strip()
    
    level_dict = {1: "Easy", 2: "Medium", 3: "Hard"}
    difficulty = level_dict.get(p['difficulty']['level'], "Unknown")
    
    item = {
        "id": question_id,
        "title": title,
        "difficulty": difficulty,
        "slug": title_slug
    }
    problem_map[title_slug] = item
    problem_map[normalize_key(title_slug)] = item
    problem_map[normalize_key(title)] = item

# รวบรวมข้อมูลโจทย์ พร้อมแมตช์เลขข้อและ Topics
solved_problems = []

for folder in folders:
    slug = folder.replace("_", "-").lower()
    norm_key = normalize_key(folder)
    info = problem_map.get(slug) or problem_map.get(norm_key)
    
    folder_encoded = urllib.parse.quote(folder)
    link = f"[Code](./{solutions_path}/{folder_encoded})"
    
    # ค้นหา Tags ของโจทย์
    tags = tags_map.get(slug) or tags_map.get(norm_key)
    if tags is None and info:
        tags = fetch_tags_fallback(info["slug"])
    tags = tags or []
    
    if info:
        solved_problems.append({
            "id": info["id"],
            "title": info["title"],
            "difficulty": info["difficulty"],
            "tags": tags,
            "link": link
        })
    else:
        solved_problems.append({
            "id": 9999,
            "title": folder,
            "difficulty": "-",
            "tags": tags,
            "link": link
        })

# เรียงลำดับตามหมายเลขข้อ (ID) จากน้อยไปมาก
solved_problems = sorted(solved_problems, key=lambda x: x["id"])

def generate_markdown_table(problem_list, include_difficulty=True):
    if include_difficulty:
        header = "| No | Name | Difficulty | Topics | Code Link |\n| :---: | :--- | :---: | :--- | :---: |\n"
        rows = []
        for p in problem_list:
            qid = p["id"] if p["id"] != 9999 else "-"
            tags_formatted = ", ".join([f"`{t}`" for t in p["tags"]]) if p["tags"] else "-"
            rows.append(f"| {qid} | {p['title']} | {p['difficulty']} | {tags_formatted} | {p['link']} |")
    else:
        header = "| No | Name | Topics | Code Link |\n| :---: | :--- | :--- | :---: |\n"
        rows = []
        for p in problem_list:
            qid = p["id"] if p["id"] != 9999 else "-"
            tags_formatted = ", ".join([f"`{t}`" for t in p["tags"]]) if p["tags"] else "-"
            rows.append(f"| {qid} | {p['title']} | {tags_formatted} | {p['link']} |")
    return header + "\n".join(rows) + "\n"

easy_problems = [p for p in solved_problems if p["difficulty"] == "Easy"]
medium_problems = [p for p in solved_problems if p["difficulty"] == "Medium"]
hard_problems = [p for p in solved_problems if p["difficulty"] == "Hard"]

# จัดกลุ่มโจทย์ตาม Topic
topic_to_problems = {}
for p in solved_problems:
    for t in p.get("tags", []):
        if t not in topic_to_problems:
            topic_to_problems[t] = []
        topic_to_problems[t].append(p)

sorted_topics = sorted(topic_to_problems.keys(), key=lambda t: (-len(topic_to_problems[t]), t))

def to_anchor(text):
    s = text.lower().replace(" ", "-")
    return re.sub(r'[^a-z0-9\-_]', '', s)

# ----------------- สร้างเนื้อหา README.md -----------------
markdown_content = "# LeetCode Solutions\n\n"

# สารบัญนำทางข้ามแต่ละส่วน (Quick Section Navigation)
markdown_content += '<a id="contents"></a>\n'
markdown_content += "## 📌 Contents\n\n"
markdown_content += "- [📖 My LeetCode Journey](#my-leetcode-journey)\n"
markdown_content += "- [📂 Browse Problems by Category](#browse-problems)\n"
markdown_content += f"- [📋 All Solved Problems ({len(folders)} Problems)](#all-solved-problems)\n"
markdown_content += "- [⚙️ How to Set This Up Yourself](#how-to-set-this-up-yourself)\n\n"
markdown_content += "---\n\n"

# ส่วนที่ 1: ประวัติความเป็นมา
markdown_content += '### <a id="my-leetcode-journey"></a>📖 My LeetCode Journey\n\n'
markdown_content += "- **April 8, 2025:** Started solving LeetCode problems as a new hobby during the school break.\n"
markdown_content += "- **End of 2025:** Reached a net total of 643 solved problems.\n"
markdown_content += "- **May 21, 2026:** Successfully crossed the milestone of 1,000 solved problems!\n"
markdown_content += "- **Purpose:** This repository serves as a personal archive to store and showcase all the coding solutions I've submitted.\n\n"
markdown_content += "[⬆️ Back to Contents](#contents)\n\n"
markdown_content += "---\n\n"

# ส่วนที่ 2: สถิติแยกตามหมวดหมู่ (พร้อมลิงก์ไปยังไฟล์แยก)
markdown_content += '### <a id="browse-problems"></a>📂 Browse Problems\n\n'
markdown_content += f"- 🟢 **[Easy Problems ({len(easy_problems)})](./EASY.md)**\n"
markdown_content += f"- 🟡 **[Medium Problems ({len(medium_problems)})](./MEDIUM.md)**\n"
markdown_content += f"- 🔴 **[Hard Problems ({len(hard_problems)})](./HARD.md)**\n"
markdown_content += f"- 📚 **[Problems by Topics ({len(sorted_topics)} Topics)](./TOPICS.md)**\n\n"
markdown_content += "[⬆️ Back to Contents](#contents)\n\n"
markdown_content += "---\n\n"

# ส่วนที่ 3: สถิติและตารางสารบัญรวม
markdown_content += f'### <a id="all-solved-problems"></a>📋 All Solved Problems ({len(folders)} Problems)\n\n'
markdown_content += generate_markdown_table(solved_problems, include_difficulty=True)
markdown_content += "\n[⬆️ Back to Contents](#contents)\n\n"

# ส่วนที่ 4: คู่มือสำหรับคนที่อยากทำตาม
markdown_content += "----\n\n"
markdown_content += '### <a id="how-to-set-this-up-yourself"></a>⚙️ How to Set This Up Yourself\n\n'
markdown_content += "If you want to sync your LeetCode submissions to GitHub and generate an organized README like this, follow these steps:\n\n"
markdown_content += "### 1. Automated Sync via GitHub Actions\n"
markdown_content += "1. Create a new GitHub repository (e.g., `leetcode-solutions`).\n"
markdown_content += "2. Get your LeetCode session cookies (`LEETCODE_SESSION` and `csrftoken`) from your browser's Developer Tools (`F12` -> Application -> Cookies -> `leetcode.com`).\n"
markdown_content += "3. In your GitHub repository, go to **Settings** -> **Secrets and variables** -> **Actions**, and add two repository secrets:\n"
markdown_content += "   - `LEETCODE_SESSION`\n"
markdown_content += "   - `CSRF_TOKEN`\n"
markdown_content += "4. Create a GitHub Action workflow file at `.github/workflows/leetcode.yml` with the following configuration:\n\n"
markdown_content += "```yaml\n"
markdown_content += "name: Sync LeetCode\n\n"
markdown_content += "on:\n"
markdown_content += "  workflow_dispatch:\n"
markdown_content += "  schedule:\n"
markdown_content += "    - cron: \"0 0 * * *\"\n\n"
markdown_content += "jobs:\n"
markdown_content += "  build:\n"
markdown_content += "    runs-on: ubuntu-latest\n"
markdown_content += "    steps:\n"
markdown_content += "      - uses: actions/checkout@v4\n"
markdown_content += "      - uses: joshcai/leetcode-sync@v1.5\n"
markdown_content += "        with:\n"
markdown_content += "          github-token: ${{ secrets.GITHUB_TOKEN }}\n"
markdown_content += "          leetcode-session: ${{ secrets.LEETCODE_SESSION }}\n"
markdown_content += "          leetcode-csrf-token: ${{ secrets.CSRF_TOKEN }}\n"
markdown_content += "          destination-folder: \"solutions\"\n"
markdown_content += "```\n\n"
markdown_content += "### 2. Generate README.md Automatically\n"
markdown_content += "You can use a Python script to scan your solution folders, fetch problem details (ID, title, difficulty) from the LeetCode API, sort them, and update your `README.md` automatically.\n\n"
markdown_content += "[⬆️ Back to Contents](#contents)\n\n"

# บันทึกไฟล์ README.md
with open("README.md", "w", encoding="utf-8") as f:
    f.write(markdown_content)

# บันทึกไฟล์ EASY.md
easy_content = f"# 🟢 LeetCode Easy Problems ({len(easy_problems)})\n\n"
easy_content += "[⬅️ Back to All Problems](./README.md) | [Problems by Topics 📚](./TOPICS.md) | [Medium Problems 🟡](./MEDIUM.md) | [Hard Problems 🔴](./HARD.md)\n\n"
easy_content += generate_markdown_table(easy_problems, include_difficulty=False)
with open("EASY.md", "w", encoding="utf-8") as f:
    f.write(easy_content)

# บันทึกไฟล์ MEDIUM.md
medium_content = f"# 🟡 LeetCode Medium Problems ({len(medium_problems)})\n\n"
medium_content += "[Easy Problems 🟢](./EASY.md) | [⬅️ Back to All Problems](./README.md) | [Problems by Topics 📚](./TOPICS.md) | [Hard Problems 🔴](./HARD.md)\n\n"
medium_content += generate_markdown_table(medium_problems, include_difficulty=False)
with open("MEDIUM.md", "w", encoding="utf-8") as f:
    f.write(medium_content)

# บันทึกไฟล์ HARD.md
hard_content = f"# 🔴 LeetCode Hard Problems ({len(hard_problems)})\n\n"
hard_content += "[Easy Problems 🟢](./EASY.md) | [Medium Problems 🟡](./MEDIUM.md) | [Problems by Topics 📚](./TOPICS.md) | [⬅️ Back to All Problems](./README.md)\n\n"
hard_content += generate_markdown_table(hard_problems, include_difficulty=False)
with open("HARD.md", "w", encoding="utf-8") as f:
    f.write(hard_content)

# บันทึกไฟล์ TOPICS.md
topics_content = f"# 📚 LeetCode Problems by Topics ({len(sorted_topics)} Topics)\n\n"
topics_content += "[⬅️ Back to All Problems](./README.md) | [Easy Problems 🟢](./EASY.md) | [Medium Problems 🟡](./MEDIUM.md) | [Hard Problems 🔴](./HARD.md)\n\n"
topics_content += "## Quick Navigation\n\n"
topics_content += "> Click on any topic to jump to its problem list.\n\n"

nav_links = [f"[`{t}` ({len(topic_to_problems[t])})](#{to_anchor(t)})" for t in sorted_topics]
topics_content += " · ".join(nav_links) + "\n\n"
topics_content += "---\n\n"

for t in sorted_topics:
    t_probs = sorted(topic_to_problems[t], key=lambda x: x["id"])
    anchor = to_anchor(t)
    topics_content += f'### <a id="{anchor}"></a>{t} ({len(t_probs)})\n\n'
    topics_content += "<details>\n"
    topics_content += f"<summary><b>View {len(t_probs)} problems</b></summary>\n\n"
    topics_content += "| No | Name | Difficulty | Code Link |\n"
    topics_content += "| :---: | :--- | :---: | :---: |\n"
    for p in t_probs:
        qid = p["id"] if p["id"] != 9999 else "-"
        topics_content += f"| {qid} | {p['title']} | {p['difficulty']} | {p['link']} |\n"
    topics_content += "\n[⬆️ Back to Top](#quick-navigation)\n\n"
    topics_content += "</details>\n\n"

with open("TOPICS.md", "w", encoding="utf-8") as f:
    f.write(topics_content)

print(f"สร้างไฟล์ README.md, EASY.md ({len(easy_problems)}), MEDIUM.md ({len(medium_problems)}), HARD.md ({len(hard_problems)}), TOPICS.md ({len(sorted_topics)} topics) สำเร็จ!")
