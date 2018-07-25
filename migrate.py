import getpass
import sys
from traceback import format_exc
import os
import base64
import stat
import argparse


class Colors:
    __black_o_green = '\x1b[5;30;42m'
    __black_o_yellow = '\x1b[5;30;43m'
    __black_o_red = '\x1b[5;30;43m'
    __end = '\x1b[0m'
    error = __black_o_red + " [ERROR] " + __end
    warning = __black_o_yellow + " [ADVERTENCIA] " + __end
    ok = __black_o_green + " [OK] " + __end


git = None

print("Comprobando paquetes necesarios...")
try:
    import pip
except Exception:
    print(Colors.error + "El paquete \'pip\' no se encuentra instalado")
    exit(-1)

try:
    from github import Github, GithubException
except Exception:
    print(Colors.warning + "Instalando paquete necesario: pygithub")
    pip.main(['install', '--user', 'pygithub'])

try:
    import numpy as np
except Exception:
    print("Instalando paquete necesario: numpy")
    pip.main(['install', '--user', 'numpy'])

print(Colors.ok + "Todos los paquetes necesarios instalados")


def status_ok(github):
    s = github.get_api_status()
    return True if s.status == 'good' else False


def download_repository(repository, path_to_download):
    """
    Download all contents at server_path with commit tag sha in
    the repository.
    """

    sha = "master"  # r.get_branch("master").commit.sha
    contents = repository.get_dir_contents(path_to_download)
    base_dir = os.path.join('test', repository.name)

    for content in contents:
        print("\tProcesando {}".format(content.path))
        if content.type == 'dir':
            download_repository(repository, content.path)
        else:
            try:
                if not os.path.exists(os.path.join(base_dir, path_to_download)):
                    os.makedirs(os.path.join(base_dir, path_to_download))
                path = content.path
                file_content = repository.get_contents(path, ref=sha)
                file_data = base64.b64decode(file_content.content)
                file_out = open(os.path.join(base_dir, path_to_download, content.name), "w")
                file_out.write(file_data.decode())
                file_out.close()
            except (GithubException, IOError) as exc:
                print('\tError al procesar {}: {}'.format(content.path, exc))


def permissions(repository):
    path = os.path.join('test', repository.name)
    # os.chmod('somefile', stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    for file in os.listdir(os.path.join(path, 'nodes')):
        if file.endswith(".py") and '__' not in file:
            try:
                print("Dando permisos de ejecución a {} ...".format(file))
                full_path = os.path.join(path, 'nodes', file)
                current_permissions = stat.S_IMODE(os.lstat(full_path).st_mode)
                os.chmod(full_path, current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                print("{} ejecutable".format(file) + Colors.ok)

            except Exception:
                print(Colors.warning + "NO se pudo dar permiso al fichero {}  :(".format(file))


def get_user_organization():
    global git

    try:
        # user = input("Usuario Github: ")
        # password = getpass.getpass(prompt='Contraseña: ', stream=sys.stderr)
        user = "Ait0r"
        password = "22593712aitor."
        git = Github(user, password)
        print("Comprobando estado de github")
        if status_ok(git):
            print("\tGithub: " + Colors.ok)
        else:
            print("\t" + Colors.error + "Api de Github no disponible")
            exit(-1)

        print("Conectando a github...")
        u = git.get_user()
        orgs = list(u.get_orgs())

        print("Entrando en organizaciones...")
        if len(orgs) > 1:
            for idx, o in enumerate(orgs):
                print("{} - {}".format(idx, o.name))
            org = input("Organización a utilizar: ")
            print("Seleccionada la organización {}".format(orgs[int(org)].name))
            org = orgs[0]
        else:
            print("Detectada solo 1 organización ({})".format(orgs[0].name))
            org = orgs[0]

        return org, u

    except Exception:
        print(format_exc())


def get_repositories(org):
    print("Accediendo a repositorios de {}".format(org.name))

    repos = list(org.get_repos())

    for idx, repo in enumerate(repos):
        print("{} - {}".format(idx, repo.name))

    not_correct = True
    to_migrate = None
    while not_correct:
        try:
            to_migrate = input("Repositorios a migrar (Separados por \" \"): ")
            to_migrate = list(map(int, to_migrate.split(" ")))
            not_correct = False
        except Exception:
            print("Error, introduce el número de repositorio de nuevo")

    if len(to_migrate) > 0:
        repos = np.array(repos)
        selected_repos = repos[to_migrate]
        print("Repositorios seleccionados: ")
        for r in selected_repos:
            print("\t{}".format(r.name))

        print("-" * 50 + "\n\n")
        for r in selected_repos:
            print("\n\nIniciando descarga de {}".format(r.name))
            download_repository(r, '')
            print(Colors.ok + "Repositorio descargado")
            print("Iniciando asignación de permisos")
            permissions(r)
    else:
        print(Colors.error + "Ningun repositorio seleccionado")
        exit(0)


def edit_bash(d):
    packages = os.listdir(d)
    bashrc = "/home/{}/.bashrc".format(getpass.getuser())
    file = open(bashrc, mode='a')
    export = "export PYTHONPATH=$PYTHONPATH:"
    file.writelines("\n\n\n#Configuracion ROS\n\n")
    for p in packages:
        path_to_add = os.path.join(os.path.abspath(p), 'src')
        line = "{}={}\n".format(p.split('-')[-1], path_to_add)
        file.writelines(line)
        export += '${}:'.format(p.split('-')[-1])

    line = "ROS=/opt/ros/kinetic/lib/python2.7/dist-packages\n"
    file.writelines(line)
    export += '${}:'.format('Ros')

    file.writelines(export[:-1])

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Directorio para realizar la migración')
    parser.add_argument('-o', action="store", dest="output_path", type=str, required=True)

    args = parser.parse_args()
    BASE_DIR = os.path.abspath(args.output_path)
    edit_bash(BASE_DIR)
    exit(0)
    print('Directorio seleccionado: {!r}'.format(BASE_DIR))
    git_org, git_user = get_user_organization()
    get_repositories(git_org)
