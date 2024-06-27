import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from configs import configure_argument_parser
from constants import BASE_DIR, ENCODING, MAIN_DOC_URL
from outputs import control_output


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = session.get(whats_new_url)
    response.encoding = ENCODING
    soup = BeautifulSoup(response.text, features='lxml')
    main_section = soup.find('section', {'id': 'what-s-new-in-python'})
    div_with_ul = main_section.find('div', {'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all('li', {'class': 'toctree-l1'})

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, автор')]
    for section in tqdm(sections_by_python):
        version_link = urljoin(whats_new_url, section.find('a')['href'])
        response = session.get(version_link)
        response.encoding = ENCODING
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = soup.find('h1')
        dl = soup.find('dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))

    return results


def latest_versions(session):
    response = session.get(MAIN_DOC_URL)
    response.encoding = ENCODING
    soup = BeautifulSoup(response.text, features='lxml')
    sidebar = soup.find('div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')

    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')

    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append((link, version, status))

    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = session.get(downloads_url)
    response.encoding = ENCODING
    soup = BeautifulSoup(response.text, features='lxml')
    div_with_table = soup.find('div', {'role': 'main'})
    table = div_with_table.find('table', {'class': 'docutils'})
    archive_url = urljoin(
        downloads_url,
        table.find('a', {'href': re.compile(r'.+pdf-a4\.zip$')})['href']
    )
    filename = archive_url.split('/')[-1]
    download_dir = BASE_DIR / 'downloads'
    download_dir.mkdir(exist_ok=True)
    archive_path = download_dir / filename
    response = session.get(archive_url)
    archive_path.write_bytes(response.content)


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
}


def main():
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)


if __name__ == '__main__':
    main()
