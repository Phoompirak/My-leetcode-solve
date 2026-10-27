import os
import re
import json
import urllib.parse
import requests

# กำหนด Path ของโฟลเดอร์โจทย์
solutions_path = "solutions/problems"
if not os.path.exists(solutions_path):
    solutions_path = "solutions"

folders = [d for d in os.listdir(solutions_path) if os.path.isdir(os.path.join(solutions_path, d))]

print(f"พบโฟลเดอร์โจทย์ทั้งหมด {len(folders)} ข้อ กำลังดึงข้อมูลจาก LeetCode...")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://leetcode.com",
    "Origin": "https://leetcode.com"
}

def normalize_key(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())

# 1. ดึงฐานข้อมูลโจทย์ทั้งหมด (มี Fallback กัน Cloudflare บล็อก)
problem_map = {}
url = "https://leetcode.com/api/problems/algorithms/"
try:
    response = requests.get(url, headers=headers, timeout=15)
    data = response.json()
    for p in data.get('stat_status_pairs', []):
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
except Exception as e:
    print(f"คำเตือน: ไม่สามารถดึงผ่าน API problems โดยตรงได้ ({e}) กำลังใช้ GraphQL สำรอง...")

# 2. ฟังก์ชันดึงรายละเอียดโจทย์รายข้อผ่าน LeetCode GraphQL
def fetch_problem_via_graphql(slug):
    query = """
    query getQuestionDetail($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionFrontendId
        title
        difficulty
        topicTags {
          name
        }
      }
    }
    """
    try:
        res = requests.post(
            "https://leetcode.com/graphql",
            json={"query": query, "variables": {"titleSlug": slug}},
            headers=headers,
            timeout=10
        )
        qdata = res.json().get('data', {}).get('question', {})
        if qdata:
            return {
                "id": int(qdata.get("questionFrontendId", 9999)),
                "title": qdata.get("title", slug),
                "difficulty": qdata.get("difficulty", "-"),
                "tags": [t["name"] for t in qdata.get("topicTags", [])]
            }
    except Exception:
        pass
    return None

# 3. ดึงข้อมูล Topics / Tags Dataset
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

# 4. รวบรวมข้อมูลโจทย์
solved_problems = []

for folder in folders:
    slug = folder.replace("_", "-").lower()
    norm_key = normalize_key(folder)
    info = problem_map.get(slug) or problem_map.get(norm_key)
    
    folder_encoded = urllib.parse.quote(folder)
    link = f"[Code](./{solutions_path}/{folder_encoded})"
    
    tags = tags_map.get(slug) or tags_map.get(norm_key) or []
    
    if not info:
        gql_info = fetch_problem_via_graphql(slug)
        if gql_info:
            info = {
                "id": gql_info["id"],
                "title": gql_info["title"],
                "difficulty": gql_info["difficulty"],
                "slug": slug
            }
            if not tags:
                tags = gql_info["tags"]

    if info:
        solved_problems.append({
            "id": info["id"],
            "title": info["title"],
            "difficulty": info["difficulty"],
            "tags": tags,
            "link": link
        })
    else:
        clean_title = folder.replace("-", " ").replace("_", " ").title()
        solved_problems.append({
            "id": 9999,
            "title": clean_title,
            "difficulty": "-",
            "tags": tags,
            "link": link
        })

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

# สร้างไฟล์ README.md
markdown_content = "# LeetCode Solutions\n\n"
markdown_content += '<a id="contents"></a>\n'
markdown_content += "## 📌 Contents\n\n"
markdown_content += "- [📂 Browse Problems by Category](#browse-problems)\n"
markdown_content += f"- [📋 All Solved Problems ({len(folders)} Problems)](#all-solved-problems)\n\n"
markdown_content += "---\n\n"

markdown_content += '### <a id="browse-problems"></a>📂 Browse Problems\n\n'
markdown_content += f"- 🟢 **[Easy Problems ({len(easy_problems)})](./EASY.md)**\n"
markdown_content += f"- 🟡 **[Medium Problems ({len(medium_problems)})](./MEDIUM.md)**\n"
markdown_content += f"- 🔴 **[Hard Problems ({len(hard_problems)})](./HARD.md)**\n"
markdown_content += f"- 📚 **[Problems by Topics ({len(sorted_topics)} Topics)](./TOPICS.md)**\n\n"
markdown_content += "[⬆️ Back to Contents](#contents)\n\n"
markdown_content += "---\n\n"

markdown_content += f'### <a id="all-solved-problems"></a>📋 All Solved Problems ({len(folders)} Problems)\n\n'
markdown_content += generate_markdown_table(solved_problems, include_difficulty=True)
markdown_content += "\n[⬆️ Back to Contents](#contents)\n"

with open("README.md", "w", encoding="utf-8") as f:
    f.write(markdown_content)

# สร้างไฟล์หมวดหมู่ EASY, MEDIUM, HARD, TOPICS
with open("EASY.md", "w", encoding="utf-8") as f:
    f.write(f"# 🟢 LeetCode Easy Problems ({len(easy_problems)})\n\n[⬅️ Back to All Problems](./README.md)\n\n" + generate_markdown_table(easy_problems, include_difficulty=False))

with open("MEDIUM.md", "w", encoding="utf-8") as f:
    f.write(f"# 🟡 LeetCode Medium Problems ({len(medium_problems)})\n\n[⬅️ Back to All Problems](./README.md)\n\n" + generate_markdown_table(medium_problems, include_difficulty=False))

with open("HARD.md", "w", encoding="utf-8") as f:
    f.write(f"# 🔴 LeetCode Hard Problems ({len(hard_problems)})\n\n[⬅️ Back to All Problems](./README.md)\n\n" + generate_markdown_table(hard_problems, include_difficulty=False))

topics_content = f"# 📚 LeetCode Problems by Topics ({len(sorted_topics)} Topics)\n\n[⬅️ Back to All Problems](./README.md)\n\n"
nav_links = [f"[`{t}` ({len(topic_to_problems[t])})](#{to_anchor(t)})" for t in sorted_topics]
topics_content += " · ".join(nav_links) + "\n\n---\n\n"

for t in sorted_topics:
    t_probs = sorted(topic_to_problems[t], key=lambda x: x["id"])
    anchor = to_anchor(t)
    topics_content += f'### <a id="{anchor}"></a>{t} ({len(t_probs)})\n\n<details>\n<summary><b>View {len(t_probs)} problems</b></summary>\n\n'
    topics_content += "| No | Name | Difficulty | Code Link |\n| :---: | :--- | :---: | :---: |\n"
    for p in t_probs:
        qid = p["id"] if p["id"] != 9999 else "-"
        topics_content += f"| {qid} | {p['title']} | {p['difficulty']} | {p['link']} |\n"
    topics_content += "\n[⬆️ Back to Top](#quick-navigation)\n</details>\n\n"

with open("TOPICS.md", "w", encoding="utf-8") as f:
    f.write(topics_content)

print(f"สร้างไฟล์ README.md, EASY.md, MEDIUM.md, HARD.md, TOPICS.md สำเร็จเรียบร้อย!")
