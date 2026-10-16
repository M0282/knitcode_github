"""Interactive local launcher; target code is never executed."""
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import webbrowser


def main():
    if sys.version_info < (3, 10):
        print('Python 3.10 이상이 필요합니다.')
        return 1
    if not shutil.which('git'):
        print('Git이 필요합니다. Git 설치 후 새 터미널에서 다시 실행하세요.')
        return 1
    print('Knitcode | GitHub 프로젝트 변경 이력 분석')
    target = input('분석할 GitHub 저장소 URL: ').strip()
    if not target.startswith(('https://github.com/', 'https://www.github.com/')):
        print('https://github.com/OWNER/REPO 형태의 주소를 입력하세요.')
        return 1
    count = input('최대 분석 커밋 수 [Enter: 500]: ').strip() or '500'
    if not count.isdigit() or int(count) < 1:
        print('커밋 수는 1 이상의 정수여야 합니다.')
        return 1
    use_api = input('Issue·PR·CI도 조회할까요? [y/N]: ').strip().lower() == 'y'
    root = Path(__file__).resolve().parent
    output = root / 'reports' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    result = subprocess.run([sys.executable, str(root / 'git_insights_cli.py'), target,
                             '--commits', count, '--output', str(output)] + (['--github-api'] if use_api else []))
    if result.returncode == 0:
        webbrowser.open((output / 'report.html').as_uri())
    return result.returncode


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print('분석을 취소했습니다.')
        raise SystemExit(1)
