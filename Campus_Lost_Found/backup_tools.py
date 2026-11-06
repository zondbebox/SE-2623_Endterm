"""Full data archive and non-destructive scratch recovery commands."""
from pathlib import Path
import json
import sys
from backup_full import BackupError, ROOT, create_full_backup, restore_full_check

def main():
    if len(sys.argv) == 2 and sys.argv[1] == 'backup':
        result = create_full_backup()
    elif len(sys.argv) in (2, 3) and sys.argv[1] == 'restore':
        if len(sys.argv) == 3:
            archive = Path(sys.argv[2])
        else:
            backups = sorted((ROOT / 'backups').glob('campus_full_*.zip'))
            if not backups:
                raise BackupError('No full archive exists. Run BACKUP.bat or bash BACKUP.sh first.')
            archive = backups[-1]
        result = restore_full_check(archive)
    else:
        raise BackupError('Use backup or restore [full-archive.zip].')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (BackupError, OSError) as error:
        print(json.dumps({'error': str(error)}), file=sys.stderr)
        raise SystemExit(1)
