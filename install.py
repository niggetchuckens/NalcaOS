import os
import sys
import subprocess

def run_command(command):
    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout.decode())
    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.decode()}")
        sys.exit(1)
        
proteus_url = 'https://learn-us-east-1-prod-fleet02-xythos.content.blackboardcdn.com/5cf94c2cf3655/18368803?X-Blackboard-S3-Bucket=learn-us-east-1-prod-fleet01-xythos&X-Blackboard-Expiration=1770595200000&X-Blackboard-Signature=NNTo10%2BS8UKDVgpOkfiuSxHUY%2Bh%2B%2FMAXPQbtTfiThsM%3D&X-Blackboard-Client-Id=340776&X-Blackboard-S3-Region=us-east-1&response-cache-control=private%2C%20max-age%3D21600&response-content-disposition=inline%3B%20filename%2A%3DUTF-8%27%27Proteus%25207.8%2520SP2.rar&response-content-type=application%2Fx-rar-compressed&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIEhzOYsrv%2Fgr5STdg%2FeBWfqafpLkvq7%2BrAMD0ci80xQcAiEA8sRR9ccHHOGhyWQTe0eMFubcsYIluEnFPMwT9e5lNSYqtAUIexAEGgw2MzU1Njc5MjQxODMiDPlDE0fsze6MVRM7dyqRBbl5sg%2FKpC79b83oJqPDUyAXbTeNAESCPf75ASM9Naicf%2FyhArzwq1P7h8FkbeVSN0FRIMyhF1KLg3l6yp%2FI3HBy550jer4urXXDxKiPxs5ed2xq13iVqTluEgiEXazvbXpneSWax9BoMDONR%2FrehzIdL2v9Eca3zBJHqsdsL7LqhVnnmUeyjL5M1yiykG4PAPNoDYIEqFbzNO4s2u%2B7DKONAy5pvNPaPEq7pIxnKOoNygn%2B9GqtreNHnsP23PzgHUot7qxh6fi7ByYRQVPDLJJIx9r8mGf5wXjRM452Rc2jUYRGeBpgDf1fT2kHi5TYhAlo4FeMm1pClzU18cgd8IV52VHA85BtQic8ycJhCs4VimrlnoJ0TmKeKUXlGWCUSBGAiYRkHlJuVoQKnuNMMVacGymZE2XJw9nu4ibCtwhsHhTmMbO2qP4AVrtOaBYA%2FcE%2Bs7mlGWJx2jMd%2BnPksMi3he4igIjIP7AnsSkhPdJnR%2FWWitKHhwbJnUgpsxbEW8uktGxTvwWOnhireLWGm9t9ICiNo0BX%2Fq3nLH7PE%2BpOJiVoiyeFoX5%2BvuSCFgVdBX0ew6Xl5nzm9ayNNd1QchXoCSXePyJXFFu5ASpI9%2BUFMRWiaRkwu21p%2BCb6E6CVHaigjyVvvwEMsbcI%2F1IkQ5AuJ0M2LLGhyLjUWPsVHKdFsnhZbmAvMiyEpmLQXuFuNPN3akrPS63IFPR1q%2F%2BHzg0DzHz4XApt2chVyT8hAFXWSn8jMO3pLMCw5V%2FCtpn6PLmbIIYnNgJ0JMmSI3hTIvUqYSQSsb2NqV%2F2UFfutTudst4jhdPnR6sYSETl66b%2BSAAKK4lW6CPINBPAKGb4t3sMrlhtSzXPSZT9n6CqQYLnyDCmoKPMBjqxAbAusdv8%2Fm2QtyMN5rp3I%2BVU5x2ts5KmKuWj0OXWB0rbty2ObzdLnos%2FWlbzdiQQpSLpgxzX1ADZPzFG2AZHa2v38ZKO9Ck5bPNpnbrphN92bYmCJv3ykj0nZkHmW4ZK0Lb734YrPaxWbC%2BXjTzW%2Fy9nMuQx8SK1CPaGpHKtBnAMrrQ0zcPugDeJvQkBQzpcHxcI47RMDU38fLDiWTNsWCZ1EQsQ5LsPvpjrIcm8KiJXFw%3D%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20260208T180000Z&X-Amz-SignedHeaders=host&X-Amz-Expires=21600&X-Amz-Credential=ASIAZH6WM4PLX6XCUONA%2F20260208%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=fe81f4ea70403df42cc3ebd5ec0c31c832a468902f9babda89710d6158d6668f'
        
def install_packages():
    pkgs = (
        "btop python3-virtualenv openssh-server openssh-client flatpak"
        "git curl wget unzip"
            )
    flat_pkgs = (
        "ru.linux_gaming.PortProton com.visualstudio.code org.onlyoffice.desktopeditors"
        ""
        )
    
    flatpak_cfg = run_command("sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo")
        
def main():
    print("Installing dependencies...")
    
    print("Setting up the application...")
    # Add any additional setup steps here, such as creating config files or directories
    
    print("Installation complete!")