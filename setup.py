from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="realtime-notes-api",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Kubernetes-native service for real-time, multi-user Markdown note editing with semantic AI search",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/realtime-notes-api",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "ruff>=0.0.284",
            "mypy>=1.5.1",
        ],
        "faiss": ["faiss-cpu>=1.8.0"],
    },
)
