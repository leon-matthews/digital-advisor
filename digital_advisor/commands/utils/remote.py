
def sudo_install(connection, source, dest, *, owner='root', group='root', mode='0600'):
    """
    Helper which installs a file with arbitrary permissions and ownership

    This is a replacement for Fabric 1's `put(..., use_sudo=True)` and adds the
    ability to set the expected ownership and permissions in one operation.
    """
    mktemp_result = connection.run('mktemp', hide='out')
    assert mktemp_result.ok
    temp_file = mktemp_result.stdout.strip()

    try:
        connection.put(source, temp_file)
        connection.sudo(f'install -o {owner} -g {group} -m {mode} {temp_file} {dest}')
    finally:
        connection.run(f'rm {temp_file}')
