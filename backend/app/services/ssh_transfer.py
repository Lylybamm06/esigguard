import paramiko
import os


def transfer_file_to_azure(local_path: str, remote_filename: str):
    """
    Envoie le fichier sur la VM dans le dossier test_emails.
    Le conteneur Docker doit monter ce dossier vers /mnt/emails.
    """

    ssh_host = os.getenv("SSH_HOST")
    ssh_user = os.getenv("SSH_USER")
    ssh_password = os.getenv("SSH_PASSWORD")

    if not all([ssh_host, ssh_user, ssh_password]):
        raise RuntimeError(
            "SSH_HOST / SSH_USER / SSH_PASSWORD doivent être définis dans backend/.env "
            "(voir backend/.env.example)"
        )

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh.connect(
        hostname=ssh_host,
        username=ssh_user,
        password=ssh_password
    )

    sftp = ssh.open_sftp()

    remote_path = (
        f"/home/azureuser/esigguard/services/cyber/"
        f"Microservices_application/test_emails/{remote_filename}"
    )

    sftp.put(local_path, remote_path)

    sftp.close()
    ssh.close()

    # Nettoyage local
    os.remove(local_path)

    return remote_path
