from cru import CruUserFriendlyException

from ._app import create_app


def main():
    app = create_app()
    app.run_command()


if __name__ == "__main__":
    try:
        main()
    except CruUserFriendlyException as e:
        print(f"Error: {e.user_message}")
        exit(1)
