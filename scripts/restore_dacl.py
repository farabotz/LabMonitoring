"""Pulihkan DACL satu file workspace; tidak menyentuh owner/SACL atau privilege OS."""
import json
from pathlib import Path
import sys
import win32security as security


def main():
    root = Path(__file__).resolve().parent.parent
    backup = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
    target = Path(backup["path"]).resolve(strict=True)
    if not target.is_relative_to(root) or not target.is_file():
        raise SystemExit("Target rollback harus satu file di workspace.")
    descriptor = security.ConvertStringSecurityDescriptorToSecurityDescriptor(
        backup["sddl"], security.SDDL_REVISION_1)
    protected = descriptor.GetSecurityDescriptorControl()[0] & security.SE_DACL_PROTECTED
    flags = security.DACL_SECURITY_INFORMATION | (
        security.PROTECTED_DACL_SECURITY_INFORMATION if protected else security.UNPROTECTED_DACL_SECURITY_INFORMATION)
    security.SetNamedSecurityInfo(str(target), security.SE_FILE_OBJECT, flags, None, None,
                                 descriptor.GetSecurityDescriptorDacl(), None)


if __name__ == "__main__":
    main()
