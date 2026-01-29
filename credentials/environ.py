


import os



class Environ:
    githublogin = os.getenv("GITHUB_LOGIN")
    githubtoken = os.getenv("GITHUB_TOKEN")
    mailadress  = os.getenv("MAIL_ADRESS")
    phonenumber = os.getenv("PHONE_NUMBER")
    ippublic    = os.getenv("IP_PUBLIC")
    ipprivate   = os.getenv("IP_PRIVATE")
    sshkey      = os.getenv("SSH_KEY")

