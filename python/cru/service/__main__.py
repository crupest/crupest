import sys

from cru import CruException

from ._app import create_app


def main():
    app = create_app()
    app.run_command()


if __name__ == "__main__":
    version_info = sys.version_info
    if not (version_info.major == 3 and version_info.minor >= 11):
        print("This application requires Python 3.11 or later.", file=sys.stderr)
        sys.exit(1)

    try:
        main()
    except CruException as e:
        user_message = e.get_user_message()
        if user_message is not None:
            print(f"Error: {user_message}")
            exit(1)
        else:
            raise
