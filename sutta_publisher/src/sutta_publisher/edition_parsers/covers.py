import base64
import json
import os
import shutil
import tempfile
import time
import typing

from jinja2 import Environment, FileSystemLoader
from pdf2image import convert_from_path
from selenium import webdriver

CALCULATED_PRINT_OPTIONS = {
    "landscape": False,
    "displayHeaderFooter": False,
    "printBackground": True,
    "preferCSSPageSize": False,
    "scale": 1.0,
    "pageRanges": "1",
    "marginTop": 0.0,
    "marginBottom": 0.0,
    "marginLeft": 0.0,
    "marginRight": 0.0,
}

DESIRED_DPI = 8.0
CUSTOM_FLAGS = [
    "--no-sandbox",
    "--disable-gpu",
    "--autoplay-policy=no-user-gesture-required",
    "--no-first-run",
    "--use-fake-ui-for-media-stream",
    "--use-fake-device-for-media-stream",
    "--disable-sync",
    "--single-process",
    "--disable-dev-shm-usage",
    f"--force-device-scale-factor={DESIRED_DPI}",
    "--hide-scrollbars",
]

CONTENT_SOURCE_DIR = "/covers"


def send_devtools(driver: webdriver.Chrome, cmd: str, params: dict[str, object] = {}) -> bytes:
    resource = "/session/%s/chromium/send_command_and_get_result" % driver.session_id
    url = driver.command_executor._url + resource
    body = json.dumps({"cmd": cmd, "params": params})
    response = driver.command_executor._request("POST", url, body)
    if response.get("status"):
        raise Exception(response.get("value"))
    _ = response.get("value")
    return base64.b64decode(_["data"])


def setup_viewer(window_size: tuple[int, int] = (1800, 2700)) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    for flag in CUSTOM_FLAGS:
        options.add_argument(flag)
    options.headless = True

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(*window_size)
    return driver


def make_raw_screenshot(output_path: str, viewer: webdriver.Chrome) -> None:
    viewer.save_screenshot(output_path)


def make_pdf(
    output_path: str,
    viewer: webdriver.Chrome,
    width: float = 6.0,
    height: float = 9.0,
) -> None:
    with open(output_path, "wb") as f:
        print_options = {"paperWidth": width, "paperHeight": height}
        print_options.update(CALCULATED_PRINT_OPTIONS)  # type: ignore
        result = send_devtools(viewer, "Page.printToPDF", print_options)  # type: ignore
        f.write(result)


def make_hires_screenshot(output_path: str, viewer: webdriver.Chrome, pdf_path: str = None, dpi: int = 300) -> None:
    if pdf_path is None:
        _, pdf_path = tempfile.mkstemp()
        make_pdf(pdf_path, viewer=viewer)

    pages = convert_from_path(pdf_path, dpi=dpi)
    pages[0].save(output_path, "JPEG", jpegopt={"quality": 100})


def copy_content(output_dir: str) -> None:
    shutil.copytree(CONTENT_SOURCE_DIR, output_dir)


def prepare_cover_html(work_dir: str, template_file_name: str, **kwargs: dict[str, typing.Any]) -> None:
    copy_content(work_dir)

    file_loader = FileSystemLoader(work_dir)
    env = Environment(loader=file_loader, autoescape=True)
    env.trim_blocks = True
    env.lstrip_blocks = True
    env.rstrip_blocks = True  # type: ignore
    template = env.get_template(template_file_name)
    output = template.render(**kwargs)

    template_path = os.path.join(work_dir, f"out_{template_file_name}")
    with open(template_path, "w") as _file:
        _file.write(output)


def make_cover(
    template_file_name: str,
    template_vars: dict[str, typing.Any],
    jpg: bool = True,
    pdf: bool = False,
    raw_screenshot: bool = False,
    width: float = 6.0,
    height: float = 9.0,
    dpi: int = 300,
) -> dict[str, str]:
    tmpdir = tempfile.mkdtemp()
    output_dir = os.path.join(tmpdir, "covers")
    prepare_cover_html(output_dir, template_file_name, **template_vars)

    viewer = setup_viewer()
    url = f"file://{output_dir}/out_{template_file_name}"
    viewer.get(url)
    time.sleep(1)

    paths = {}

    if raw_screenshot:
        raw_path = os.path.join(tmpdir, "raw_cover.png")
        make_raw_screenshot(raw_path, viewer=viewer)
        paths["raw_screenshot"] = raw_path

    if pdf:
        pdf_path = os.path.join(tmpdir, "cover.pdf")
        make_pdf(pdf_path, viewer=viewer, width=width, height=height)
        paths["pdf"] = pdf_path
    else:
        pdf_path = None

    if jpg:
        jpg_path = os.path.join(tmpdir, "cover.jpg")
        make_hires_screenshot(jpg_path, viewer=viewer, pdf_path=pdf_path, dpi=300)
        paths["jpg"] = jpg_path

    return paths
