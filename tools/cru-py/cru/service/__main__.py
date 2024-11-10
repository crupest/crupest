from cru import CruException

from ._app import create_app


def main():
    app = create_app()
    app.run_command()


if __name__ == "__main__":
    try:
        main()
    except CruException as e:
        user_message = e.get_user_message()
        if user_message is not None:
            print(f"Error: {user_message}")
            exit(1)
        else:
            raise
