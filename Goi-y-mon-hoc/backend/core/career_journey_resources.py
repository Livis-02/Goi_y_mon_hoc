"""
Resources cho từng milestone trong career exploration journey.

Mapping: (target_career_code, sequence) → list[Resource]
- sequence 1: Hiểu nghề (read/watch)
- sequence 2: Học thử module (do)
- sequence 3: Hỏi anh/chị khoá trên (connect)
- sequence 4: Reflection (built-in modal — không cần resource)

Mỗi resource:
{
  "type": "read" | "watch" | "do" | "tip",
  "label": str,
  "url": str | None,
  "duration_min": int | None,   # ước lượng thời gian
}

Admin có thể edit dict này. Career code không có entry sẽ fallback về `_DEFAULT_RESOURCES`.
"""
from __future__ import annotations


# Resources chung — fallback cho career chưa có dữ liệu cụ thể
_DEFAULT_RESOURCES: dict[int, list[dict]] = {
    1: [
        {"type": "read", "label": "Tìm bài viết \"A Day in Life of {career}\" trên Medium hoặc Reddit /r/cscareerquestions", "url": None, "duration_min": 20},
        {"type": "watch", "label": "Xem 1 video YouTube tổng quan về nghề (15-30 phút)", "url": None, "duration_min": 30},
        {"type": "tip", "label": "Sau khi xong, ghi 3 điểm em ấn tượng hoặc lo ngại nhất.", "url": None, "duration_min": None},
    ],
    2: [
        {"type": "do", "label": "Coursera: Tìm khoá free liên quan, học 1-2 module đầu", "url": "https://www.coursera.org/", "duration_min": 180},
        {"type": "do", "label": "freeCodeCamp: Bài tập tay (free)", "url": "https://www.freecodecamp.org/", "duration_min": 120},
        {"type": "do", "label": "YouTube: \"crash course\" series (3-5 video)", "url": "https://www.youtube.com/", "duration_min": 90},
        {"type": "tip", "label": "Mục tiêu: cảm nhận thực sự công việc làm gì hằng ngày, không phải master kỹ năng.", "url": None, "duration_min": None},
    ],
    3: [
        {"type": "do", "label": "LinkedIn: search \"{career} Vietnam K17-K20\", gửi tin nhắn xin 15 phút phỏng vấn", "url": "https://www.linkedin.com/", "duration_min": 30},
        {"type": "do", "label": "Hỏi anh/chị khoá trên ở khoa hoặc qua nhóm CLB", "url": None, "duration_min": 60},
        {"type": "tip", "label": "3 câu hỏi gợi ý: (1) Ngày làm việc trông ra sao? (2) Skill nào dùng nhiều nhất? (3) Tiếc gì khi học ĐH?", "url": None, "duration_min": None},
    ],
    4: [],  # Reflection — không cần resource
}


# Override per-career — admin edit ở đây
_CAREER_OVERRIDES: dict[str, dict[int, list[dict]]] = {
    "data_scientist": {
        1: [
            {"type": "read", "label": "Towards Data Science: \"What Does a Data Scientist Actually Do?\"", "url": "https://towardsdatascience.com/", "duration_min": 20},
            {"type": "watch", "label": "Krish Naik: \"Day in Life of a Data Scientist\" (YouTube)", "url": "https://www.youtube.com/results?search_query=day+in+life+of+data+scientist", "duration_min": 25},
            {"type": "read", "label": "Reddit /r/datascience — top posts của tháng", "url": "https://www.reddit.com/r/datascience/top/", "duration_min": 30},
            {"type": "tip", "label": "Ghi note: tỷ lệ ML/business/SQL/visualization trong công việc thực — sẽ surprise em.", "url": None, "duration_min": None},
        ],
        2: [
            {"type": "do", "label": "Kaggle: Titanic competition (beginner-friendly, ~3 giờ)", "url": "https://www.kaggle.com/c/titanic", "duration_min": 180},
            {"type": "do", "label": "Coursera: \"Python for Data Science\" by IBM (free audit)", "url": "https://www.coursera.org/learn/python-for-applied-data-science-ai", "duration_min": 240},
            {"type": "do", "label": "Andrew Ng's Machine Learning (week 1-2)", "url": "https://www.coursera.org/learn/machine-learning", "duration_min": 300},
        ],
        3: [
            {"type": "do", "label": "LinkedIn: \"Data Scientist Vietnam K17-K20\" — gửi tin nhắn xin 15p", "url": "https://www.linkedin.com/search/results/people/?keywords=data%20scientist%20vietnam", "duration_min": 30},
            {"type": "tip", "label": "Hỏi: Junior DS thực sự code Python bao nhiêu / SQL bao nhiêu? Có dùng deep learning không?", "url": None, "duration_min": None},
        ],
    },
    "ml_engineer": {
        1: [
            {"type": "read", "label": "Made With ML — overview MLOps & ML Engineering", "url": "https://madewithml.com/", "duration_min": 30},
            {"type": "watch", "label": "Chip Huyen: \"Real-world ML challenges\" (YouTube)", "url": "https://www.youtube.com/results?search_query=chip+huyen+ml+production", "duration_min": 40},
        ],
        2: [
            {"type": "do", "label": "Hugging Face course (free, hands-on)", "url": "https://huggingface.co/learn/nlp-course", "duration_min": 240},
            {"type": "do", "label": "Fast.ai Practical Deep Learning (week 1)", "url": "https://course.fast.ai/", "duration_min": 180},
        ],
        3: [
            {"type": "do", "label": "Kaggle Vietnam community Slack/Facebook", "url": "https://www.facebook.com/groups/kagglevietnam", "duration_min": 30},
        ],
    },
    "frontend_dev": {
        1: [
            {"type": "read", "label": "frontend.guide — overview vai trò Frontend", "url": "https://roadmap.sh/frontend", "duration_min": 20},
            {"type": "watch", "label": "Theo - t3.gg: Frontend career advice", "url": "https://www.youtube.com/@t3dotgg", "duration_min": 30},
        ],
        2: [
            {"type": "do", "label": "freeCodeCamp: \"Responsive Web Design\" (free certificate)", "url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "duration_min": 600},
            {"type": "do", "label": "Frontend Mentor: 1 challenge \"Newbie\" tier", "url": "https://www.frontendmentor.io/challenges?difficulties=1", "duration_min": 240},
            {"type": "do", "label": "React Tutorial chính thức", "url": "https://react.dev/learn", "duration_min": 180},
        ],
        3: [
            {"type": "do", "label": "Discord Reactiflux — Việt Nam channel hoặc \"junior-jobs\"", "url": "https://www.reactiflux.com/", "duration_min": 30},
        ],
    },
    "backend": {
        1: [
            {"type": "read", "label": "roadmap.sh: Backend Developer roadmap", "url": "https://roadmap.sh/backend", "duration_min": 25},
            {"type": "watch", "label": "ByteByteGo: \"What does a Backend engineer do?\"", "url": "https://www.youtube.com/@ByteByteGo", "duration_min": 30},
        ],
        2: [
            {"type": "do", "label": "Build a REST API: FastAPI tutorial chính thức", "url": "https://fastapi.tiangolo.com/tutorial/", "duration_min": 240},
            {"type": "do", "label": "PostgreSQL tutorial: pgexercises.com", "url": "https://pgexercises.com/", "duration_min": 180},
        ],
        3: [
            {"type": "do", "label": "Vietnam Backend Engineers Facebook group", "url": "https://www.facebook.com/groups/vietnambackend", "duration_min": 30},
        ],
    },
    "devops": {
        1: [
            {"type": "read", "label": "Google SRE Book: Chapter 1 (free)", "url": "https://sre.google/sre-book/introduction/", "duration_min": 30},
            {"type": "watch", "label": "TechWorld with Nana: \"What is DevOps?\"", "url": "https://www.youtube.com/@TechWorldwithNana", "duration_min": 30},
        ],
        2: [
            {"type": "do", "label": "KodeKloud: Linux Foundations (free tier)", "url": "https://kodekloud.com/", "duration_min": 240},
            {"type": "do", "label": "Docker Tutorial chính thức", "url": "https://docs.docker.com/get-started/", "duration_min": 180},
            {"type": "do", "label": "Kubernetes Basics: kubernetes.io/docs/tutorials/", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "duration_min": 180},
        ],
        3: [
            {"type": "do", "label": "Vietnam DevOps Community (Facebook/Discord)", "url": "https://www.facebook.com/groups/vietnamdevops", "duration_min": 30},
        ],
    },
    "security": {
        1: [
            {"type": "read", "label": "OWASP Top 10 (cybersec basics)", "url": "https://owasp.org/Top10/", "duration_min": 30},
            {"type": "watch", "label": "John Hammond: \"Cybersecurity careers\"", "url": "https://www.youtube.com/@_JohnHammond", "duration_min": 25},
        ],
        2: [
            {"type": "do", "label": "TryHackMe: \"Pre Security\" path (free)", "url": "https://tryhackme.com/path/outline/presecurity", "duration_min": 600},
            {"type": "do", "label": "PicoCTF: 5 challenges easy tier", "url": "https://play.picoctf.org/", "duration_min": 240},
        ],
        3: [
            {"type": "do", "label": "WhiteHat.vn community", "url": "https://whitehat.vn/", "duration_min": 30},
        ],
    },
    "mobile_dev": {
        1: [
            {"type": "read", "label": "roadmap.sh: Android Developer", "url": "https://roadmap.sh/android", "duration_min": 25},
            {"type": "watch", "label": "Philipp Lackner: \"Modern Android dev\"", "url": "https://www.youtube.com/@PhilippLackner", "duration_min": 30},
        ],
        2: [
            {"type": "do", "label": "Android Codelabs (Google official)", "url": "https://developer.android.com/courses", "duration_min": 360},
            {"type": "do", "label": "Flutter Tutorial chính thức", "url": "https://flutter.dev/learn", "duration_min": 240},
        ],
        3: [
            {"type": "do", "label": "Vietnam Mobile Developers Facebook", "url": "https://www.facebook.com/groups/vnmobileapp", "duration_min": 30},
        ],
    },
    "network_admin": {
        1: [
            {"type": "read", "label": "Cisco \"What is Networking?\"", "url": "https://www.cisco.com/c/en/us/solutions/enterprise-networks/what-is-networking.html", "duration_min": 20},
            {"type": "watch", "label": "Network Chuck: \"Day in life of Network Admin\"", "url": "https://www.youtube.com/@NetworkChuck", "duration_min": 30},
        ],
        2: [
            {"type": "do", "label": "Cisco Networking Academy: Intro to Networks (free)", "url": "https://www.netacad.com/courses/networking", "duration_min": 600},
            {"type": "do", "label": "Practical Networking on YouTube", "url": "https://www.youtube.com/@PracticalNetworking", "duration_min": 240},
        ],
        3: [
            {"type": "do", "label": "VietNetwork Vietnam (Facebook group)", "url": "https://www.facebook.com/groups/vietnetwork", "duration_min": 30},
        ],
    },
}


_TASK_KIND_BY_SEQUENCE = {1: "understand", 2: "try", 3: "connect", 4: "reflect"}


def get_resources(target_career: str | None, sequence: int) -> list[dict]:
    """Return resources for a milestone (career_code, sequence)."""
    seq = int(sequence)
    if target_career and target_career in _CAREER_OVERRIDES:
        career_map = _CAREER_OVERRIDES[target_career]
        if seq in career_map:
            return career_map[seq]
    # Fallback: use defaults but interpolate {career} placeholder
    defaults = _DEFAULT_RESOURCES.get(seq, [])
    if target_career:
        return [
            {**r, "label": r["label"].replace("{career}", target_career)}
            for r in defaults
        ]
    return defaults


def get_task_kind(sequence: int) -> str:
    """Return UI kind: 'understand' | 'try' | 'connect' | 'reflect'."""
    return _TASK_KIND_BY_SEQUENCE.get(int(sequence), "do")
