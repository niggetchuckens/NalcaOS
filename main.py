if __name__ == "__main__":
    from configs.installer import Installer
    installer = Installer(input("Enter your username: "), input("Enter your password: "))
    installer.run()