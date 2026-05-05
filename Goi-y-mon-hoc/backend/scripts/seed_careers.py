"""Seed 7 career paths with skills, course mappings, and domain profiles.

Run: python -m backend.scripts.seed_careers
Idempotent: uses ON CONFLICT DO NOTHING semantics via model-level check.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.db.db import SessionLocal
from backend.db import models


# ── Domain keys used in domain_profile + course tags ──────────────────────────
# Each course is auto-tagged by name/code patterns; each career has weights in [0,1].
DOMAINS = [
    "programming", "algorithms", "database", "networking", "web",
    "mobile", "ai_ml", "security", "devops", "data_analytics",
    "math", "software_engineering",
]


CAREERS = [
    {
        "code": "backend",
        "name": "Lập trình Backend",
        "icon": "dns",
        "color": "indigo",
        "short_description": "Xây dựng API, xử lý logic server, quản lý cơ sở dữ liệu cho ứng dụng web/mobile.",
        "long_description": "Backend developer viết mã phía server xử lý logic nghiệp vụ, quản lý database, tích hợp API, và đảm bảo hiệu năng. Hướng đi phù hợp với SV thích giải thuật, tư duy hệ thống, và cơ sở dữ liệu.",
        "domain_profile": {
            "programming": 0.95, "algorithms": 0.8, "database": 0.95,
            "networking": 0.7, "web": 0.8, "software_engineering": 0.9,
            "devops": 0.6, "security": 0.5, "math": 0.3, "ai_ml": 0.2,
            "mobile": 0.2, "data_analytics": 0.4,
        },
        "skills": [
            ("Python (Django / FastAPI)", "language", "intermediate", 1, "official_docs", "FastAPI Documentation", "https://fastapi.tiangolo.com/", "Framework phổ biến cho REST API + async I/O.", 60),
            ("Node.js (Express / NestJS)", "language", "intermediate", 2, "udemy", "Node.js Complete Guide", "https://www.udemy.com/course/nodejs-the-complete-guide/", "Runtime JavaScript cho backend, dễ học cho SV đã biết JS.", 50),
            ("PostgreSQL / MySQL nâng cao", "tool", "intermediate", 1, "book", "Use The Index, Luke!", "https://use-the-index-luke.com/", "Hiểu index, query plan, tối ưu câu truy vấn — khác với SQL cơ bản ở trường.", 30),
            ("Redis (cache + queue)", "tool", "basic", 2, "official_docs", "Redis University", "https://university.redis.com/", "Cache, session, pub/sub — kỹ năng gần như bắt buộc.", 20),
            ("Docker + Docker Compose", "tool", "intermediate", 1, "coursera", "Docker for Developers (IBM)", "https://www.coursera.org/learn/docker-containers-for-developers", "Đóng gói app, chạy multi-service local.", 25),
            ("REST + OpenAPI design", "skill", "intermediate", 1, "book", "REST API Design Rulebook", "https://www.oreilly.com/library/view/rest-api-design/9781449317904/", "Nguyên tắc thiết kế API chuẩn industry.", 15),
            ("Git + Git Flow / Trunk-based", "tool", "basic", 1, "official_docs", "Pro Git Book", "https://git-scm.com/book", "Quản lý mã nguồn đội nhóm.", 10),
            ("AWS / GCP cơ bản", "tool", "basic", 2, "certification", "AWS Cloud Practitioner", "https://aws.amazon.com/certification/certified-cloud-practitioner/", "Hiểu EC2, S3, RDS, IAM — chuẩn bị deploy.", 40),
            ("Unit testing (pytest / Jest)", "skill", "intermediate", 1, "book", "Python Testing with pytest", "https://pragprog.com/titles/bopytest2/python-testing-with-pytest-second-edition/", "Viết test cho logic nghiệp vụ.", 20),
            ("System Design basics", "skill", "intermediate", 2, "coursera", "Grokking System Design", "https://www.designgurus.io/course/grokking-the-system-design-interview", "Chuẩn bị phỏng vấn và thiết kế hệ thống.", 40),
            ("CI/CD (GitHub Actions)", "tool", "basic", 3, "official_docs", "GitHub Actions Docs", "https://docs.github.com/en/actions", "Pipeline tự động build + deploy.", 15),
            ("TypeScript (cho Node stack)", "language", "basic", 3, "official_docs", "TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/", "Nếu theo stack JS/Node.", 25),
        ],
        "domain_hints": {"programming": True, "database": True, "algorithms": True, "software_engineering": True},
    },
    {
        "code": "frontend",
        "name": "Lập trình Frontend",
        "icon": "web",
        "color": "sky",
        "short_description": "Xây dựng giao diện người dùng responsive, tương tác phong phú, hiệu năng cao.",
        "long_description": "Frontend developer chịu trách nhiệm phần người dùng thấy: UI/UX, state management, tích hợp API. Phù hợp với SV có thẩm mỹ, thích sản phẩm trực quan, sáng tạo.",
        "domain_profile": {
            "programming": 0.85, "web": 0.95, "software_engineering": 0.7,
            "mobile": 0.5, "algorithms": 0.5, "database": 0.3,
            "networking": 0.3, "devops": 0.3, "security": 0.4, "math": 0.2, "ai_ml": 0.1,
            "data_analytics": 0.2,
        },
        "skills": [
            ("React (hoặc Vue) nâng cao", "framework", "intermediate", 1, "official_docs", "React Docs (mới)", "https://react.dev/learn", "Core: hooks, context, suspense.", 50),
            ("TypeScript", "language", "intermediate", 1, "official_docs", "TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/", "Phần lớn dự án production dùng TS.", 30),
            ("State management (Redux Toolkit / Zustand)", "tool", "intermediate", 2, "udemy", "React + Redux Complete", "https://www.udemy.com/course/react-redux/", "Quản lý state phức tạp.", 20),
            ("Tailwind CSS + design system", "tool", "basic", 1, "official_docs", "Tailwind Docs", "https://tailwindcss.com/docs", "Styling hiện đại, tốc độ dev nhanh.", 15),
            ("Next.js / Remix (SSR)", "framework", "intermediate", 2, "official_docs", "Next.js Learn", "https://nextjs.org/learn", "SEO, SSR, edge rendering.", 40),
            ("Web performance (Core Web Vitals)", "skill", "intermediate", 2, "coursera", "web.dev Performance", "https://web.dev/learn/performance", "Tối ưu LCP, CLS, INP.", 20),
            ("Accessibility (WCAG 2.1)", "skill", "basic", 2, "official_docs", "MDN Accessibility", "https://developer.mozilla.org/en-US/docs/Web/Accessibility", "Xây UI cho mọi người dùng.", 15),
            ("Figma — đọc hiểu design", "tool", "basic", 1, "official_docs", "Figma Academy", "https://www.figma.com/resources/learn-design/", "Làm việc với designer.", 10),
            ("Testing UI (Vitest + Playwright)", "skill", "intermediate", 2, "official_docs", "Playwright Docs", "https://playwright.dev/docs/intro", "Unit + E2E testing cho frontend.", 25),
            ("GraphQL (Apollo / Relay)", "tool", "basic", 3, "official_docs", "How to GraphQL", "https://www.howtographql.com/", "Thay thế REST trong nhiều dự án mới.", 25),
            ("Mobile-first responsive design", "skill", "basic", 1, "book", "Responsive Web Design (A Book Apart)", "https://abookapart.com/products/responsive-web-design", "CSS grid, flexbox, media queries.", 15),
        ],
        "domain_hints": {"programming": True, "web": True, "software_engineering": True},
    },
    {
        "code": "fullstack",
        "name": "Lập trình Fullstack",
        "icon": "layers",
        "color": "emerald",
        "short_description": "Kết hợp backend + frontend, phù hợp startup, freelancer, dự án nhỏ-vừa.",
        "long_description": "Fullstack developer làm cả FE + BE, thường trong team nhỏ hoặc khi cần phát triển nhanh. Đòi hỏi kiến thức rộng, không sâu tối đa ở một mảng.",
        "domain_profile": {
            "programming": 0.95, "web": 0.9, "database": 0.8, "algorithms": 0.7,
            "software_engineering": 0.85, "networking": 0.5, "devops": 0.6,
            "security": 0.5, "mobile": 0.3, "math": 0.3, "ai_ml": 0.2,
            "data_analytics": 0.3,
        },
        "skills": [
            ("JavaScript/TypeScript thành thạo", "language", "intermediate", 1, "official_docs", "MDN JavaScript Guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "Ngôn ngữ chính của stack JS fullstack.", 40),
            ("Node.js + Express/NestJS", "framework", "intermediate", 1, "udemy", "NestJS Zero to Hero", "https://www.udemy.com/course/nestjs-zero-to-hero/", "Backend JS thông dụng.", 50),
            ("React + Next.js", "framework", "intermediate", 1, "official_docs", "Next.js App Router", "https://nextjs.org/docs/app", "Frontend + SSR trong 1 framework.", 40),
            ("PostgreSQL + Prisma/Drizzle ORM", "tool", "intermediate", 1, "official_docs", "Prisma Docs", "https://www.prisma.io/docs", "ORM hiện đại với type-safe queries.", 25),
            ("Docker + đóng gói dự án", "tool", "basic", 2, "coursera", "Docker for Developers", "https://www.coursera.org/learn/docker-containers-for-developers", "Deploy local + production.", 20),
            ("Vercel / Netlify / Railway deploy", "tool", "basic", 2, "official_docs", "Vercel Docs", "https://vercel.com/docs", "Platform-as-a-service cho fullstack nhanh.", 10),
            ("Authentication (OAuth2, JWT)", "skill", "intermediate", 1, "book", "OAuth 2 in Action", "https://www.manning.com/books/oauth-2-in-action", "Login, SSO, refresh token.", 25),
            ("REST + GraphQL hybrid", "skill", "basic", 2, "official_docs", "GraphQL Docs", "https://graphql.org/learn/", "Linh hoạt chọn theo yêu cầu.", 20),
            ("Git + pair/mob programming", "skill", "basic", 1, "book", "Team Topologies", "https://teamtopologies.com/book", "Cộng tác đội nhỏ.", 10),
            ("Basic DevOps (GitHub Actions + Docker)", "tool", "basic", 2, "official_docs", "GitHub Actions Docs", "https://docs.github.com/en/actions", "Tự động hóa build/deploy.", 20),
        ],
        "domain_hints": {"programming": True, "web": True, "database": True, "software_engineering": True},
    },
    {
        "code": "data_science",
        "name": "Data Science / ML Engineer",
        "icon": "psychology",
        "color": "purple",
        "short_description": "Phân tích dữ liệu, xây dựng mô hình ML/DL, hỗ trợ ra quyết định.",
        "long_description": "Data scientist khai thác dữ liệu tìm insight, kỹ sư ML đưa mô hình vào production. Đòi hỏi toán, thống kê, Python, và tư duy thực nghiệm.",
        "domain_profile": {
            "math": 0.95, "ai_ml": 0.95, "programming": 0.85, "data_analytics": 0.95,
            "algorithms": 0.8, "database": 0.7, "software_engineering": 0.6,
            "web": 0.2, "mobile": 0.1, "networking": 0.2, "devops": 0.5, "security": 0.3,
        },
        "skills": [
            ("Python (numpy, pandas, scikit-learn)", "language", "intermediate", 1, "coursera", "Python for Everybody (U Michigan)", "https://www.coursera.org/specializations/python", "Stack chuẩn cho Data Science.", 80),
            ("Thống kê ứng dụng + Xác suất", "skill", "intermediate", 1, "book", "Think Stats 2 (Allen Downey)", "https://greenteapress.com/thinkstats2/", "Nền tảng, KHÔNG thể bỏ qua.", 60),
            ("Deep Learning (PyTorch / TensorFlow)", "framework", "intermediate", 1, "coursera", "Deep Learning Specialization (Andrew Ng)", "https://www.coursera.org/specializations/deep-learning", "Neural networks, CNN, RNN, Transformer.", 120),
            ("SQL nâng cao + Data Warehousing", "tool", "intermediate", 1, "book", "SQL for Data Analysis", "https://www.oreilly.com/library/view/sql-for-data/9781492088776/", "Window functions, CTE, tối ưu.", 30),
            ("Kaggle competitions (top 30%)", "skill", "intermediate", 2, "udemy", "Kaggle Pandas Course", "https://www.kaggle.com/learn/pandas", "Kinh nghiệm thực chiến.", 60),
            ("MLOps (MLflow, DVC)", "tool", "basic", 2, "official_docs", "MLflow Docs", "https://mlflow.org/docs/latest/index.html", "Versioning model + pipeline.", 30),
            ("Data Visualization (matplotlib, Plotly)", "tool", "basic", 1, "book", "Storytelling with Data", "https://www.storytellingwithdata.com/book", "Truyền đạt insight bằng biểu đồ.", 20),
            ("AWS SageMaker hoặc GCP Vertex AI", "certification", "basic", 3, "certification", "AWS ML Specialty", "https://aws.amazon.com/certification/certified-machine-learning-specialty/", "Triển khai model trên cloud.", 50),
            ("NLP foundations", "skill", "intermediate", 2, "coursera", "HuggingFace Course", "https://huggingface.co/learn/nlp-course", "Đặc biệt cần cho 2026 với LLM bùng nổ.", 50),
            ("Big Data (Spark cơ bản)", "tool", "basic", 3, "official_docs", "Apache Spark Docs", "https://spark.apache.org/docs/latest/", "Xử lý dữ liệu lớn khi pandas không đủ.", 30),
        ],
        "domain_hints": {"math": True, "ai_ml": True, "data_analytics": True, "programming": True, "algorithms": True},
    },
    {
        "code": "devops",
        "name": "DevOps / Cloud Engineer",
        "icon": "cloud",
        "color": "amber",
        "short_description": "Tự động hóa CI/CD, quản lý hạ tầng cloud, đảm bảo uptime, monitoring.",
        "long_description": "DevOps engineer cầu nối dev + ops, xây dựng pipeline, quản lý Kubernetes/Terraform, xử lý sự cố production. Phù hợp với SV thích hệ thống và automation.",
        "domain_profile": {
            "devops": 0.95, "networking": 0.85, "security": 0.75, "programming": 0.7,
            "software_engineering": 0.8, "database": 0.6, "algorithms": 0.5,
            "web": 0.4, "mobile": 0.1, "math": 0.2, "ai_ml": 0.15, "data_analytics": 0.4,
        },
        "skills": [
            ("Linux system administration", "skill", "intermediate", 1, "book", "The Linux Command Line (William Shotts)", "http://linuxcommand.org/tlcl.php", "Bash, file permissions, systemd.", 40),
            ("Docker + Kubernetes", "tool", "intermediate", 1, "certification", "CKA — Certified Kubernetes Admin", "https://www.cncf.io/training/certification/cka/", "Orchestration là skill cốt lõi DevOps.", 80),
            ("Terraform / Pulumi (IaC)", "tool", "intermediate", 1, "official_docs", "Terraform Learn", "https://developer.hashicorp.com/terraform/tutorials", "Khai báo hạ tầng bằng code.", 40),
            ("AWS / GCP / Azure (ít nhất 1)", "certification", "intermediate", 1, "certification", "AWS Solutions Architect Associate", "https://aws.amazon.com/certification/certified-solutions-architect-associate/", "Cloud là chuẩn industry.", 100),
            ("CI/CD (Jenkins / GitHub Actions / GitLab CI)", "tool", "intermediate", 1, "official_docs", "GitHub Actions Docs", "https://docs.github.com/en/actions", "Tự động hóa pipeline.", 30),
            ("Monitoring (Prometheus + Grafana)", "tool", "basic", 2, "official_docs", "Prometheus Docs", "https://prometheus.io/docs/", "Metrics, alerting.", 25),
            ("Logging (ELK / Loki)", "tool", "basic", 2, "book", "Learning Elastic Stack", "https://www.oreilly.com/library/view/learning-elastic-stack/9781787281868/", "Tập trung log, query nhanh.", 20),
            ("Networking cơ bản (TCP/IP, DNS, HTTP)", "skill", "intermediate", 1, "book", "TCP/IP Illustrated Vol 1", "https://www.oreilly.com/library/view/tcpip-illustrated-volume/9780132808200/", "Nền tảng hiểu hệ thống phân tán.", 40),
            ("Bash / Python scripting", "language", "intermediate", 1, "book", "Python for DevOps", "https://www.oreilly.com/library/view/python-for-devops/9781492057680/", "Tự động hóa task thường nhật.", 30),
            ("Security hardening (basic)", "skill", "basic", 2, "certification", "CompTIA Security+", "https://www.comptia.org/certifications/security", "Hardening OS + container.", 40),
        ],
        "domain_hints": {"devops": True, "networking": True, "programming": True, "software_engineering": True},
    },
    {
        "code": "security",
        "name": "An toàn Thông tin (Security)",
        "icon": "security",
        "color": "red",
        "short_description": "Bảo vệ hệ thống, kiểm tra lỗ hổng, ứng phó sự cố, pentest.",
        "long_description": "Security engineer bảo vệ ứng dụng + hạ tầng, làm pentest, forensics, hoặc xây blue-team. Cần tư duy phản biện, nền tảng mạng + hệ điều hành vững.",
        "domain_profile": {
            "security": 0.98, "networking": 0.9, "programming": 0.7, "algorithms": 0.6,
            "devops": 0.7, "software_engineering": 0.6, "database": 0.5,
            "web": 0.6, "mobile": 0.3, "math": 0.4, "ai_ml": 0.2, "data_analytics": 0.4,
        },
        "skills": [
            ("Networking foundations (OSI, TCP/IP)", "skill", "intermediate", 1, "certification", "CompTIA Network+", "https://www.comptia.org/certifications/network", "Hiểu tầng thấp trước khi hack.", 40),
            ("Linux + Windows internals", "skill", "intermediate", 1, "book", "Linux Basics for Hackers (OccupyTheWeb)", "https://nostarch.com/linuxbasicsforhackers", "Hiểu OS = hiểu cách exploit.", 40),
            ("Penetration Testing hands-on", "certification", "intermediate", 1, "certification", "OSCP (Offensive Security)", "https://www.offsec.com/courses/pen-200/", "Chứng chỉ cực uy tín, thực chiến.", 200),
            ("Web Security (OWASP Top 10)", "skill", "intermediate", 1, "official_docs", "OWASP Top 10", "https://owasp.org/www-project-top-ten/", "SQL injection, XSS, CSRF, SSRF...", 30),
            ("CTF practice (HackTheBox / TryHackMe)", "skill", "intermediate", 2, "udemy", "TryHackMe Learning Paths", "https://tryhackme.com/paths", "Kinh nghiệm thực tế.", 80),
            ("Cryptography basics", "skill", "basic", 2, "coursera", "Cryptography I (Stanford)", "https://www.coursera.org/learn/crypto", "AES, RSA, TLS handshake.", 40),
            ("Reverse engineering (Ghidra / IDA)", "tool", "advanced", 3, "book", "Practical Malware Analysis", "https://nostarch.com/malware", "Malware + binary analysis.", 80),
            ("SIEM + Blue team basics", "tool", "basic", 2, "certification", "CompTIA CySA+", "https://www.comptia.org/certifications/cybersecurity-analyst", "Nếu thiên về defensive.", 40),
            ("Python cho scripting exploit/tool", "language", "intermediate", 1, "book", "Black Hat Python (No Starch)", "https://nostarch.com/black-hat-python2E", "Viết tool nhỏ, parse output.", 30),
            ("Compliance + risk (ISO 27001, NIST)", "skill", "basic", 3, "official_docs", "NIST Cybersecurity Framework", "https://www.nist.gov/cyberframework", "Cần cho vị trí GRC.", 30),
        ],
        "domain_hints": {"security": True, "networking": True, "programming": True},
    },
    {
        "code": "mobile",
        "name": "Lập trình Mobile",
        "icon": "smartphone",
        "color": "teal",
        "short_description": "Xây dựng app iOS/Android, native hoặc cross-platform (Flutter, React Native).",
        "long_description": "Mobile developer xây dựng trải nghiệm mobile. Có thể chọn native (Swift/Kotlin) cho hiệu năng cao, hoặc cross-platform để tốc độ phát triển.",
        "domain_profile": {
            "mobile": 0.98, "programming": 0.9, "software_engineering": 0.8,
            "web": 0.5, "algorithms": 0.6, "database": 0.6,
            "networking": 0.5, "devops": 0.3, "security": 0.4, "math": 0.3,
            "ai_ml": 0.2, "data_analytics": 0.2,
        },
        "skills": [
            ("Kotlin + Android Jetpack", "language", "intermediate", 1, "official_docs", "Android Developers Codelabs", "https://developer.android.com/courses", "Nền tảng chính Android hiện đại.", 80),
            ("Swift + SwiftUI (iOS)", "language", "intermediate", 1, "official_docs", "Apple — Develop in Swift", "https://developer.apple.com/tutorials/swiftui", "Native iOS.", 80),
            ("Flutter (cross-platform)", "framework", "intermediate", 1, "official_docs", "Flutter Codelabs", "https://docs.flutter.dev/codelabs", "1 codebase cho cả 2 nền tảng.", 60),
            ("React Native", "framework", "intermediate", 2, "official_docs", "React Native Docs", "https://reactnative.dev/docs/getting-started", "Stack JS cho mobile.", 50),
            ("Architecture (MVVM / Clean)", "skill", "intermediate", 1, "book", "Clean Architecture (Uncle Bob)", "https://www.oreilly.com/library/view/clean-architecture-a/9780134494272/", "Tách biệt UI khỏi logic.", 30),
            ("Offline-first + local DB (Room / Core Data)", "skill", "basic", 2, "official_docs", "Android Room Guide", "https://developer.android.com/training/data-storage/room", "App chạy offline.", 25),
            ("App performance profiling", "skill", "intermediate", 2, "official_docs", "Android Profiler", "https://developer.android.com/studio/profile", "Tối ưu memory, battery, frame rate.", 25),
            ("Push notifications + background tasks", "skill", "basic", 2, "official_docs", "Firebase Cloud Messaging", "https://firebase.google.com/docs/cloud-messaging", "FCM / APNs.", 20),
            ("Publishing (App Store / Play Store)", "skill", "basic", 2, "official_docs", "App Store Review Guidelines", "https://developer.apple.com/app-store/review/guidelines/", "Quy trình release + review.", 15),
            ("Testing (Espresso / XCTest)", "skill", "basic", 3, "official_docs", "Android Testing Fundamentals", "https://developer.android.com/training/testing/fundamentals", "Unit + UI test cho mobile.", 25),
        ],
        "domain_hints": {"mobile": True, "programming": True, "software_engineering": True},
    },
]


# ── Course → domain tags heuristic ────────────────────────────────────────────
DOMAIN_KEYWORDS = {
    "programming":         ["lập trình", "lap trinh", "python", "java", "c++", "c #", "c#", " c ", "javascript", "nhập môn", "kỹ thuật lập trình"],
    "algorithms":          ["giải thuật", "thuật toán", "cấu trúc dữ liệu", "ctdl", "algorithm"],
    "database":            ["cơ sở dữ liệu", "csdl", "database", "sql", "nosql", "data warehouse"],
    "networking":          ["mạng", "mạng máy tính", "network", "truyền thông"],
    "web":                 ["web", "html", "css", "front-end", "backend", "javascript"],
    "mobile":              ["di động", "mobile", "android", "ios"],
    "ai_ml":               ["trí tuệ nhân tạo", "học máy", "machine learning", "deep", "ai", "ttnt", "nlp"],
    "security":            ["an toàn", "an ninh", "bảo mật", "security", "atn"],
    "devops":              ["hệ điều hành", "triển khai", "cloud", "docker", "kub"],
    "data_analytics":      ["khai phá dữ liệu", "dữ liệu", "phân tích", "data mining", "analytics", "bi"],
    "math":                ["toán", "giải tích", "đại số", "xác suất", "thống kê", "rời rạc", "discrete", "calculus", "algebra"],
    "software_engineering":["phần mềm", "công nghệ phần mềm", "quản trị dự án", "đồ án", "phân tích thiết kế"],
}


def _infer_course_domains(course_name: str, course_code: str) -> dict[str, float]:
    """Return {domain: weight} for a given course based on its name."""
    n = (course_name or "").lower()
    tags: dict[str, float] = {}
    for domain, kws in DOMAIN_KEYWORDS.items():
        for kw in kws:
            if kw in n:
                tags[domain] = max(tags.get(domain, 0.0), 1.0)
                break
    return tags


def _cosine_sim(v1: dict[str, float], v2: dict[str, float]) -> float:
    import math
    keys = set(v1.keys()) | set(v2.keys())
    dot = sum(v1.get(k, 0.0) * v2.get(k, 0.0) for k in keys)
    n1 = math.sqrt(sum(v * v for v in v1.values()))
    n2 = math.sqrt(sum(v * v for v in v2.values()))
    return dot / (n1 * n2) if n1 and n2 else 0.0


def seed():
    db = SessionLocal()
    try:
        created = 0
        for c in CAREERS:
            existing = db.query(models.CareerPath).filter(models.CareerPath.code == c["code"]).first()
            if existing:
                existing.name = c["name"]
                existing.icon = c["icon"]
                existing.color = c["color"]
                existing.short_description = c["short_description"]
                existing.long_description = c["long_description"]
                existing.domain_profile = c["domain_profile"]
                cp = existing
            else:
                cp = models.CareerPath(
                    code=c["code"],
                    name=c["name"],
                    icon=c["icon"],
                    color=c["color"],
                    short_description=c["short_description"],
                    long_description=c["long_description"],
                    domain_profile=c["domain_profile"],
                )
                db.add(cp)
                db.flush()
                created += 1

            # Replace skills (idempotent: delete+insert)
            db.query(models.CareerSkill).filter(models.CareerSkill.path_id == cp.id).delete()
            for (name, stype, level, prio, src_type, src_name, src_url, descr, hours) in c["skills"]:
                db.add(models.CareerSkill(
                    path_id=cp.id,
                    skill_name=name,
                    skill_type=stype,
                    level=level,
                    priority=prio,
                    source_type=src_type,
                    source_name=src_name,
                    source_url=src_url,
                    description=descr,
                    estimated_hours=hours,
                ))

            # Replace course mapping via cosine sim between course domains + career profile
            db.query(models.CareerCourseMap).filter(models.CareerCourseMap.path_id == cp.id).delete()
            courses = db.query(models.Course).all()
            for course in courses:
                course_domains = _infer_course_domains(course.course_name or "", course.course_code or "")
                if not course_domains:
                    continue
                sim = _cosine_sim(course_domains, c["domain_profile"])
                if sim >= 0.35:
                    db.add(models.CareerCourseMap(
                        path_id=cp.id,
                        course_code=course.course_code,
                        relevance=round(min(1.0, sim), 2),
                    ))
        db.commit()
        total_skills = db.query(models.CareerSkill).count()
        total_mappings = db.query(models.CareerCourseMap).count()
        print(f"Seed OK. Careers created: {created} (total: {len(CAREERS)}).")
        print(f"Total skills: {total_skills}, total course mappings: {total_mappings}.")
    finally:
        db.close()


if __name__ == "__main__":
    import sys as _sys
    try:
        _sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    seed()
