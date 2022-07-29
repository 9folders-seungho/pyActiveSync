from ping import PingProcess


def ping_process(user):
    ping_process = PingProcess(
        user.get("email"), user.get("password"), user.get("server_uri")
    )

    print("RUN PING {}".format(ping_process))
    response = ping_process.run_ping()
    print("RESPONSE: {}".format(response))


user = {
    "email": "seungho.jung@ninefolders.xyz",
    "type": "basicauth",
    "password": "re:work@1001",
    "server_uri": "mail.ninefolders.xyz",
}


def check_user(user):
    while True:
        print(user)
        print("create process")
        ping_process(user=user)


check_user(user=user)
