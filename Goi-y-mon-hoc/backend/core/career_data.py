"""
Career learning path data: 5 tracks, skills, curated free resources.
Course codes mapped from CTDT 7480201.
"""

CAREER_TRACKS: dict[str, dict] = {
    "backend": {
        "name": "Backend Developer",
        "icon": "dns",
        "color": "#3b82f6",
        "desc": "Xây dựng server, REST API, cơ sở dữ liệu — nền tảng cho mọi ứng dụng web/mobile",
        "skills": [
            {
                "id": "oop",
                "name": "Lập trình hướng đối tượng",
                "level": "foundation",
                "school_courses": ["7080216", "7080512"],
                "school_covered": True,
                "resources": [
                    {"title": "Python OOP – Corey Schafer", "url": "https://www.youtube.com/playlist?list=PL-osiE80TeTsqhIuOqKhwlXsIBIdSeYtc", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                    {"title": "Java OOP – Bro Code", "url": "https://www.youtube.com/watch?v=6T_HgnjoYwM", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "dsa",
                "name": "Cấu trúc dữ liệu & Thuật toán",
                "level": "foundation",
                "school_courses": ["7080206"],
                "school_covered": True,
                "resources": [
                    {"title": "Algorithms – Abdul Bari", "url": "https://www.youtube.com/watch?v=0IAPZzGSbME&list=PLDN4rrl48XKpZkf03iYFl-O29szjTrs_O", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                    {"title": "LeetCode – luyện thuật toán", "url": "https://leetcode.com/", "type": "practice", "provider": "LeetCode", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "sql",
                "name": "SQL & Database Design",
                "level": "foundation",
                "school_courses": ["7080207", "7080211"],
                "school_covered": True,
                "resources": [
                    {"title": "SQLZoo – thực hành SQL tương tác", "url": "https://sqlzoo.net/", "type": "practice", "provider": "SQLZoo", "is_free": True, "lang": "en"},
                    {"title": "Mode SQL Tutorial", "url": "https://mode.com/sql-tutorial/", "type": "course", "provider": "Mode", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "git",
                "name": "Git & Version Control",
                "level": "foundation",
                "school_courses": ["7080111"],
                "school_covered": True,
                "resources": [
                    {"title": "Pro Git Book (miễn phí)", "url": "https://git-scm.com/book/vi/v2", "type": "book", "provider": "Git-scm", "is_free": True, "lang": "vi"},
                    {"title": "Git & GitHub – freeCodeCamp", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "rest_api",
                "name": "REST API & HTTP",
                "level": "intermediate",
                "school_courses": ["7080116"],
                "school_covered": True,
                "resources": [
                    {"title": "FastAPI Official Tutorial", "url": "https://fastapi.tiangolo.com/tutorial/", "type": "docs", "provider": "FastAPI", "is_free": True, "lang": "en"},
                    {"title": "REST API – freeCodeCamp", "url": "https://www.youtube.com/watch?v=WXsD0ZgxjRw", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "linux",
                "name": "Linux & Command Line",
                "level": "intermediate",
                "school_courses": ["7080112"],
                "school_covered": True,
                "resources": [
                    {"title": "Linux Journey (tự học online)", "url": "https://linuxjourney.com/", "type": "course", "provider": "Linux Journey", "is_free": True, "lang": "en"},
                    {"title": "Missing Semester – MIT", "url": "https://missing.csail.mit.edu/", "type": "course", "provider": "MIT", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "python_backend",
                "name": "Python cho Backend",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "CS50P – Python (Harvard, miễn phí)", "url": "https://cs50.harvard.edu/python/", "type": "course", "provider": "Harvard", "is_free": True, "lang": "en"},
                    {"title": "Python Backend – Corey Schafer", "url": "https://www.youtube.com/watch?v=MwZwr5Tvyxo", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "docker",
                "name": "Docker & Containers",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Docker Tutorial – TechWorld with Nana", "url": "https://www.youtube.com/watch?v=3c-iBn73dDE", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                    {"title": "Play with Docker – lab online", "url": "https://labs.play-with-docker.com/", "type": "practice", "provider": "Docker", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "system_design",
                "name": "System Design",
                "level": "advanced",
                "school_courses": ["7080113"],
                "school_covered": True,
                "resources": [
                    {"title": "System Design Primer (GitHub)", "url": "https://github.com/donnemartin/system-design-primer", "type": "article", "provider": "GitHub", "is_free": True, "lang": "en"},
                    {"title": "ByteByteGo – System Design", "url": "https://www.youtube.com/@ByteByteGo", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "microservices",
                "name": "Microservices & Architecture",
                "level": "advanced",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Microservices – freeCodeCamp", "url": "https://www.youtube.com/watch?v=rv4LlmLmVWk", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                    {"title": "Viblo – Microservices Architecture", "url": "https://viblo.asia/tags/microservices", "type": "article", "provider": "Viblo", "is_free": True, "lang": "vi"},
                ],
            },
        ],
    },

    "frontend": {
        "name": "Frontend / Mobile Developer",
        "icon": "smartphone",
        "color": "#8b5cf6",
        "desc": "Xây dựng giao diện người dùng cho web và ứng dụng di động",
        "skills": [
            {
                "id": "html_css",
                "name": "HTML & CSS",
                "level": "foundation",
                "school_courses": ["7080116"],
                "school_covered": True,
                "resources": [
                    {"title": "The Odin Project – HTML/CSS (miễn phí)", "url": "https://www.theodinproject.com/paths/foundations", "type": "course", "provider": "Odin Project", "is_free": True, "lang": "en"},
                    {"title": "freeCodeCamp Responsive Design", "url": "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "type": "course", "provider": "freeCodeCamp", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "javascript",
                "name": "JavaScript",
                "level": "foundation",
                "school_courses": ["7080116"],
                "school_covered": True,
                "resources": [
                    {"title": "JavaScript.info – hướng dẫn đầy đủ", "url": "https://javascript.info/", "type": "course", "provider": "javascript.info", "is_free": True, "lang": "en"},
                    {"title": "JS Crash Course – Traversy Media", "url": "https://www.youtube.com/watch?v=hdI2bqOjy3c", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "git_fe",
                "name": "Git & Tooling",
                "level": "foundation",
                "school_courses": ["7080111"],
                "school_covered": True,
                "resources": [
                    {"title": "Pro Git Book", "url": "https://git-scm.com/book/vi/v2", "type": "book", "provider": "Git-scm", "is_free": True, "lang": "vi"},
                ],
            },
            {
                "id": "typescript",
                "name": "TypeScript",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "TypeScript Handbook (Official)", "url": "https://www.typescriptlang.org/docs/handbook/", "type": "docs", "provider": "TypeScript", "is_free": True, "lang": "en"},
                    {"title": "TypeScript – Net Ninja", "url": "https://www.youtube.com/playlist?list=PL4cUxeGkcC9gUgr39Q_yD6v-bSyMwKPUI", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "react",
                "name": "React",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "React Official Docs (learn.react.dev)", "url": "https://react.dev/learn", "type": "docs", "provider": "React", "is_free": True, "lang": "en"},
                    {"title": "Scrimba React Course (miễn phí)", "url": "https://scrimba.com/learn/learnreact", "type": "course", "provider": "Scrimba", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "flutter",
                "name": "Flutter & Dart",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Flutter Official Codelabs", "url": "https://docs.flutter.dev/get-started/codelab", "type": "docs", "provider": "Flutter", "is_free": True, "lang": "en"},
                    {"title": "Flutter Tutorial – Net Ninja", "url": "https://www.youtube.com/playlist?list=PL4cUxeGkcC9jLYyp2Aoh6hcWuxFDX6PBJ", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "ui_ux",
                "name": "UI/UX Cơ bản",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Figma Learn Design", "url": "https://www.figma.com/resources/learn-design/", "type": "course", "provider": "Figma", "is_free": True, "lang": "en"},
                    {"title": "Google UX Design – Coursera (audit free)", "url": "https://www.coursera.org/professional-certificates/google-ux-design", "type": "course", "provider": "Coursera", "is_free": False, "lang": "en"},
                ],
            },
            {
                "id": "web_performance",
                "name": "Web Performance",
                "level": "advanced",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "web.dev – Google Performance Guide", "url": "https://web.dev/learn/performance", "type": "course", "provider": "Google", "is_free": True, "lang": "en"},
                ],
            },
        ],
    },

    "ai_ml": {
        "name": "AI / ML Engineer",
        "icon": "psychology",
        "color": "#f59e0b",
        "desc": "Xây dựng mô hình học máy, xử lý dữ liệu, tích hợp AI vào sản phẩm thực tế",
        "skills": [
            {
                "id": "math_ml",
                "name": "Toán học cho ML",
                "level": "foundation",
                "school_courses": ["7010102", "7010120", "7010103", "7010104"],
                "school_covered": True,
                "resources": [
                    {"title": "3Blue1Brown – Linear Algebra", "url": "https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                    {"title": "Khan Academy – Statistics & Probability", "url": "https://www.khanacademy.org/math/statistics-probability", "type": "course", "provider": "Khan Academy", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "python_ds",
                "name": "Python cho Data Science",
                "level": "foundation",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Kaggle Python Course (miễn phí)", "url": "https://www.kaggle.com/learn/python", "type": "course", "provider": "Kaggle", "is_free": True, "lang": "en"},
                    {"title": "Kaggle Pandas Course (miễn phí)", "url": "https://www.kaggle.com/learn/pandas", "type": "course", "provider": "Kaggle", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "ml_fundamentals",
                "name": "Học máy cơ bản",
                "level": "foundation",
                "school_courses": ["7080122"],
                "school_covered": True,
                "resources": [
                    {"title": "fast.ai – Practical Deep Learning (miễn phí)", "url": "https://course.fast.ai/", "type": "course", "provider": "fast.ai", "is_free": True, "lang": "en"},
                    {"title": "Andrew Ng ML Course – Coursera (audit)", "url": "https://www.coursera.org/specializations/machine-learning-introduction", "type": "course", "provider": "Coursera", "is_free": False, "lang": "en"},
                ],
            },
            {
                "id": "data_analysis",
                "name": "Phân tích & Khai phá dữ liệu",
                "level": "intermediate",
                "school_courses": ["7080509", "7080508"],
                "school_covered": True,
                "resources": [
                    {"title": "Kaggle Data Visualization (miễn phí)", "url": "https://www.kaggle.com/learn/data-visualization", "type": "course", "provider": "Kaggle", "is_free": True, "lang": "en"},
                    {"title": "Viblo – Data Mining với Python", "url": "https://viblo.asia/tags/data-mining", "type": "article", "provider": "Viblo", "is_free": True, "lang": "vi"},
                ],
            },
            {
                "id": "deep_learning",
                "name": "Deep Learning",
                "level": "intermediate",
                "school_courses": ["7080510"],
                "school_covered": True,
                "resources": [
                    {"title": "d2l.ai – Dive into Deep Learning (miễn phí)", "url": "https://d2l.ai/", "type": "book", "provider": "d2l.ai", "is_free": True, "lang": "en"},
                    {"title": "PyTorch Official Tutorial", "url": "https://pytorch.org/tutorials/", "type": "docs", "provider": "PyTorch", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "nlp",
                "name": "NLP – Xử lý Ngôn ngữ Tự nhiên",
                "level": "advanced",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Hugging Face NLP Course (miễn phí)", "url": "https://huggingface.co/learn/nlp-course/", "type": "course", "provider": "Hugging Face", "is_free": True, "lang": "en"},
                    {"title": "Stanford CS224N NLP (YouTube)", "url": "https://www.youtube.com/playlist?list=PLoROMvodv4rMFqRtEuo6SGjY4XbRIVx76", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "mlops",
                "name": "MLOps & Deployment",
                "level": "advanced",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "MLOps Zoomcamp (miễn phí – GitHub)", "url": "https://github.com/DataTalksClub/mlops-zoomcamp", "type": "course", "provider": "DataTalksClub", "is_free": True, "lang": "en"},
                    {"title": "Made With ML – MLOps Guide", "url": "https://madewithml.com/", "type": "course", "provider": "Made With ML", "is_free": True, "lang": "en"},
                ],
            },
        ],
    },

    "devops": {
        "name": "DevOps / Cloud Engineer",
        "icon": "cloud",
        "color": "#10b981",
        "desc": "Vận hành hạ tầng, CI/CD, triển khai và scale ứng dụng trên cloud",
        "skills": [
            {
                "id": "linux_devops",
                "name": "Linux & Shell Scripting",
                "level": "foundation",
                "school_courses": ["7080112"],
                "school_covered": True,
                "resources": [
                    {"title": "Linux Journey (tự học online)", "url": "https://linuxjourney.com/", "type": "course", "provider": "Linux Journey", "is_free": True, "lang": "en"},
                    {"title": "Missing Semester – MIT", "url": "https://missing.csail.mit.edu/", "type": "course", "provider": "MIT", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "networking_devops",
                "name": "Networking Fundamentals",
                "level": "foundation",
                "school_courses": ["7080717"],
                "school_covered": True,
                "resources": [
                    {"title": "Computer Networking – freeCodeCamp", "url": "https://www.youtube.com/watch?v=qiQR5rTSshw", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "git_devops",
                "name": "Git & Open Source",
                "level": "foundation",
                "school_courses": ["7080111"],
                "school_covered": True,
                "resources": [
                    {"title": "Pro Git Book", "url": "https://git-scm.com/book/vi/v2", "type": "book", "provider": "Git-scm", "is_free": True, "lang": "vi"},
                ],
            },
            {
                "id": "docker_devops",
                "name": "Docker",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Docker Tutorial – TechWorld with Nana", "url": "https://www.youtube.com/watch?v=3c-iBn73dDE", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                    {"title": "Play with Docker – lab online", "url": "https://labs.play-with-docker.com/", "type": "practice", "provider": "Docker", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "cicd",
                "name": "CI/CD (GitHub Actions)",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "GitHub Actions – Official Docs", "url": "https://docs.github.com/en/actions", "type": "docs", "provider": "GitHub", "is_free": True, "lang": "en"},
                    {"title": "CI/CD Pipeline – TechWorld with Nana", "url": "https://www.youtube.com/watch?v=R8_veQiYBjI", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "cloud",
                "name": "Cloud (AWS / GCP)",
                "level": "intermediate",
                "school_courses": ["7080504"],
                "school_covered": True,
                "resources": [
                    {"title": "AWS Free Tier + Skill Builder", "url": "https://aws.amazon.com/free/", "type": "practice", "provider": "AWS", "is_free": True, "lang": "en"},
                    {"title": "Google Cloud Skills Boost (free tier)", "url": "https://www.cloudskillsboost.google/", "type": "course", "provider": "Google Cloud", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "kubernetes",
                "name": "Kubernetes",
                "level": "advanced",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Kubernetes Docs – Official Tutorial", "url": "https://kubernetes.io/docs/tutorials/", "type": "docs", "provider": "Kubernetes", "is_free": True, "lang": "en"},
                    {"title": "Kubernetes Full Course – freeCodeCamp", "url": "https://www.youtube.com/watch?v=X48VuDVv0do", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "iac",
                "name": "Infrastructure as Code (Terraform)",
                "level": "advanced",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Terraform Tutorial – freeCodeCamp", "url": "https://www.youtube.com/watch?v=SLB_c_ayRMo", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                    {"title": "HashiCorp Terraform Docs", "url": "https://developer.hashicorp.com/terraform/tutorials", "type": "docs", "provider": "HashiCorp", "is_free": True, "lang": "en"},
                ],
            },
        ],
    },

    "security": {
        "name": "Security / Network Engineer",
        "icon": "security",
        "color": "#ef4444",
        "desc": "Bảo mật hệ thống, kiểm thử xâm nhập, vận hành mạng an toàn",
        "skills": [
            {
                "id": "networking_sec",
                "name": "Networking & TCP/IP",
                "level": "foundation",
                "school_courses": ["7080717"],
                "school_covered": True,
                "resources": [
                    {"title": "Professor Messer – CompTIA Network+", "url": "https://www.youtube.com/@professormesser", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                    {"title": "Computer Networking – freeCodeCamp", "url": "https://www.youtube.com/watch?v=qiQR5rTSshw", "type": "video", "provider": "YouTube", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "linux_sec",
                "name": "Linux & Hệ điều hành",
                "level": "foundation",
                "school_courses": ["7080112"],
                "school_covered": True,
                "resources": [
                    {"title": "OverTheWire: Bandit – học Linux qua CTF", "url": "https://overthewire.org/wargames/bandit/", "type": "practice", "provider": "OverTheWire", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "crypto",
                "name": "Mật mã học & PKI",
                "level": "foundation",
                "school_courses": ["7080703"],
                "school_covered": True,
                "resources": [
                    {"title": "Cryptography I – Stanford (Coursera audit)", "url": "https://www.coursera.org/learn/crypto", "type": "course", "provider": "Coursera", "is_free": True, "lang": "en"},
                    {"title": "CryptoHack – học mật mã qua thực hành", "url": "https://cryptohack.org/", "type": "practice", "provider": "CryptoHack", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "web_security",
                "name": "Web Security & OWASP",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "PortSwigger Web Security Academy (miễn phí)", "url": "https://portswigger.net/web-security", "type": "course", "provider": "PortSwigger", "is_free": True, "lang": "en"},
                    {"title": "OWASP Top 10 – Official Guide", "url": "https://owasp.org/www-project-top-ten/", "type": "docs", "provider": "OWASP", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "pentesting",
                "name": "Penetration Testing",
                "level": "intermediate",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "TryHackMe – thực hành bảo mật (free tier)", "url": "https://tryhackme.com/", "type": "practice", "provider": "TryHackMe", "is_free": True, "lang": "en"},
                    {"title": "picoCTF – CTF cho người mới", "url": "https://picoctf.org/", "type": "practice", "provider": "picoCTF", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "network_admin",
                "name": "Quản trị mạng & IoT",
                "level": "intermediate",
                "school_courses": ["7080713", "7080517"],
                "school_covered": True,
                "resources": [
                    {"title": "Cisco Packet Tracer – mô phỏng mạng (miễn phí)", "url": "https://www.netacad.com/courses/packet-tracer", "type": "practice", "provider": "Cisco", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "soc",
                "name": "SOC & Incident Response",
                "level": "advanced",
                "school_courses": [],
                "school_covered": False,
                "resources": [
                    {"title": "Blue Team Labs Online", "url": "https://blueteamlabs.online/", "type": "practice", "provider": "BTLO", "is_free": True, "lang": "en"},
                    {"title": "LetsDefend – SOC Analyst Training", "url": "https://letsdefend.io/", "type": "course", "provider": "LetsDefend", "is_free": True, "lang": "en"},
                ],
            },
            {
                "id": "cloud_security",
                "name": "Cloud Security",
                "level": "advanced",
                "school_courses": ["7080504"],
                "school_covered": True,
                "resources": [
                    {"title": "AWS Security Fundamentals (miễn phí)", "url": "https://explore.skillbuilder.aws/learn/course/external/view/elearning/48/aws-security-fundamentals-second-edition", "type": "course", "provider": "AWS", "is_free": True, "lang": "en"},
                ],
            },
        ],
    },
}


# ML scoring: course_code -> {track_id: affinity_weight}
COURSE_TRACK_AFFINITY: dict[str, dict[str, float]] = {
    "7080208": {"backend": 0.7, "frontend": 0.5, "ai_ml": 0.6, "devops": 0.3, "security": 0.4},   # Cơ sở lập trình
    "7080216": {"backend": 0.8, "frontend": 0.5, "ai_ml": 0.6, "devops": 0.4, "security": 0.5},   # KTLT C++
    "7080512": {"backend": 0.9, "frontend": 0.6, "ai_ml": 0.5, "devops": 0.4, "security": 0.5},   # LT Java
    "7080206": {"backend": 0.9, "frontend": 0.5, "ai_ml": 0.8, "devops": 0.4, "security": 0.4},   # CTDL & GT
    "7080207": {"backend": 0.9, "frontend": 0.3, "ai_ml": 0.6, "devops": 0.4, "security": 0.3},   # CSDL
    "7080211": {"backend": 0.8, "frontend": 0.3, "ai_ml": 0.5, "devops": 0.4, "security": 0.3},   # HQ CSDL
    "7080116": {"backend": 0.7, "frontend": 1.0, "ai_ml": 0.2, "devops": 0.3, "security": 0.4},   # Phát triển Web
    "7010102": {"backend": 0.3, "frontend": 0.1, "ai_ml": 1.0, "devops": 0.2, "security": 0.2},   # Đại số tuyến tính
    "7010120": {"backend": 0.3, "frontend": 0.1, "ai_ml": 0.9, "devops": 0.2, "security": 0.2},   # XSTK
    "7010103": {"backend": 0.2, "frontend": 0.1, "ai_ml": 0.7, "devops": 0.1, "security": 0.1},   # Giải tích 1
    "7010104": {"backend": 0.2, "frontend": 0.1, "ai_ml": 0.7, "devops": 0.1, "security": 0.1},   # Giải tích 2
    "7080112": {"backend": 0.4, "frontend": 0.1, "ai_ml": 0.2, "devops": 0.9, "security": 0.8},   # Nguyên lý HĐH
    "7080717": {"backend": 0.4, "frontend": 0.2, "ai_ml": 0.2, "devops": 0.9, "security": 1.0},   # Mạng máy tính
    "7080703": {"backend": 0.3, "frontend": 0.2, "ai_ml": 0.1, "devops": 0.5, "security": 1.0},   # Cơ sở an ninh mạng
    "7080122": {"backend": 0.2, "frontend": 0.1, "ai_ml": 1.0, "devops": 0.1, "security": 0.1},   # Trí tuệ nhân tạo
    "7080509": {"backend": 0.3, "frontend": 0.1, "ai_ml": 0.9, "devops": 0.2, "security": 0.1},   # Khoa học dữ liệu
    "7080508": {"backend": 0.2, "frontend": 0.1, "ai_ml": 1.0, "devops": 0.1, "security": 0.1},   # Khai phá dữ liệu
    "7080510": {"backend": 0.2, "frontend": 0.1, "ai_ml": 1.0, "devops": 0.1, "security": 0.1},   # Kỹ nghệ TT & HM
    "7080504": {"backend": 0.4, "frontend": 0.2, "ai_ml": 0.3, "devops": 1.0, "security": 0.5},   # Điện toán đám mây
    "7080517": {"backend": 0.3, "frontend": 0.3, "ai_ml": 0.3, "devops": 0.7, "security": 0.4},   # Phát triển IoT
    "7080713": {"backend": 0.2, "frontend": 0.2, "ai_ml": 0.2, "devops": 0.8, "security": 0.6},   # Hạ tầng mạng IoT
    "7080111": {"backend": 0.5, "frontend": 0.5, "ai_ml": 0.4, "devops": 0.6, "security": 0.4},   # Mã nguồn mở
    "7080113": {"backend": 0.6, "frontend": 0.4, "ai_ml": 0.3, "devops": 0.4, "security": 0.3},   # PTKT hệ thống
    "7080515": {"backend": 0.6, "frontend": 0.5, "ai_ml": 0.3, "devops": 0.3, "security": 0.3},   # PTTK HĐT
    "7080626": {"backend": 0.4, "frontend": 0.5, "ai_ml": 0.2, "devops": 0.2, "security": 0.2},   # Thương mại điện tử
}


def score_career_fit(grades: list[dict]) -> dict[str, int]:
    """
    Input: list of {course_code, score10, passed}
    Output: {track_id: fit_percentage (0–100)}
    Weighted by grade — passing with 9.0 counts more than 5.0.
    """
    from collections import defaultdict

    numerator: dict[str, float] = defaultdict(float)
    denominator: dict[str, float] = defaultdict(float)

    for g in grades:
        if not g.get("passed"):
            continue
        code = g.get("course_code", "")
        affinity = COURSE_TRACK_AFFINITY.get(code, {})
        if not affinity:
            continue
        score_norm = min(1.0, (g.get("score10") or 5.0) / 10.0)
        for track, weight in affinity.items():
            numerator[track] += weight * score_norm
            denominator[track] += weight

    result: dict[str, int] = {}
    for track in CAREER_TRACKS:
        if denominator[track] > 0:
            result[track] = min(100, max(0, round(numerator[track] / denominator[track] * 100)))
        else:
            result[track] = 0

    return result
