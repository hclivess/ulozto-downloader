import argparse
import importlib.util
import sys
import signal
import os
from os import path
from uldlib import downloader, captcha, __version__, __path__
from uldlib.const import DEFAULT_CONN_TIMEOUT
from uldlib.frontend import ConsoleFrontend
from uldlib.utils import LogLevel


def run():
    parser = argparse.ArgumentParser(
        description='Download file from Uloz.to using multiple parallel downloads.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--url', metavar='URL', type=str, default="",
                        help="URL from Uloz.to (tip: enter in 'quotes' because the URL contains ! sign)")
    parser.add_argument('--parts', metavar='N', type=int, default=7,
                        help='Number of parts that will be downloaded in parallel')
    parser.add_argument('--output', metavar='DIRECTORY',
                        type=str, default="./", help='Target directory')
    parser.add_argument('--auto-captcha', default=False, action="store_true",
                        help='Try to solve CAPTCHAs automatically using TensorFlow')
    parser.add_argument('--manual-captcha', default=False, action="store_true",
                        help='Solve CAPTCHAs by manual input')
    parser.add_argument('--conn-timeout', metavar='SEC', default=DEFAULT_CONN_TIMEOUT, type=int,
                        help='Set connection timeout for TOR sessions in seconds')
    parser.add_argument('--version', action='version', version=__version__)


    args = parser.parse_args()

    if not args.url:
        url = input("insert url: ")
    else:
        url = args.url

    # TODO: implement other frontends and allow to choose from them
    frontend = ConsoleFrontend()

    tflite_available = importlib.util.find_spec('tflite_runtime')
    tkinter_available = importlib.util.find_spec('tkinter')

    # Autodetection
    if not args.auto_captcha and not args.manual_captcha:
        if tflite_available:
            frontend.main_log("[Autodetect] tflite_runtime available, using --auto-captcha")
            args.auto_captcha = True
        elif tkinter_available:
            frontend.main_log("[Autodetect] tkinter available, using --manual-captcha")
            args.manual_captcha = True
        else:
            frontend.main_log(
                "[Autodetect] WARNING: No tflite_runtime and no tkinter available, cannot solve CAPTCHA (only direct download available)",
                level=LogLevel.WARNING
            )

    if args.auto_captcha:
        if not tflite_available:
            frontend.main_log('ERROR: --auto-captcha used but tflite_runtime not available', level=LogLevel.ERROR)
            sys.exit(1)

        model_path = path.join(__path__[0], "model.tflite")
        model_download_url = "https://github.com/JanPalasek/ulozto-captcha-breaker/releases/download/v2.2/model.tflite"
        solver = captcha.AutoReadCaptcha(model_path, model_download_url, frontend)
    elif args.manual_captcha:
        if not tkinter_available:
            frontend.main_log('ERROR: --manual-captcha used but tkinter not available', level=LogLevel.ERROR)
            sys.exit(1)

        solver = captcha.ManualInput(frontend)
    else:
        solver = captcha.Dummy(frontend)

    # enables ansi escape characters in terminal on Windows
    if os.name == 'nt':
        os.system("")

    d = downloader.Downloader(frontend, solver)

    # Register sigint handler
    def sigint_handler(sig, frame):
        if d.terminating:
            return  # Already terminating
        d.terminate()
        print('Program terminated.')
        sys.exit(1)

    signal.signal(signal.SIGINT, sigint_handler)

    page = d.download(url, args.parts, "", 5)
    d.terminate()

    if not os.path.exists("done"):
        os.makedirs("done")
    os.remove(f"{page.filename}.cmd")
    os.rename(f"{page.filename}", f"done/{page.filename}")



