"""Host SCM opsional. Tidak dipasang otomatis dan tidak pernah menampilkan UI di Session 0."""
import os
from pathlib import Path
import threading
import win32service
import win32serviceutil
import servicemanager
from .worker import run


class LabAccessAgentService(win32serviceutil.ServiceFramework):
    _svc_name_ = "LabAccessAgent"
    _svc_display_name_ = "LabAccess Device Agent (Pilot)"
    _svc_description_ = "Heartbeat dan IPC lokal; tidak mengganti login Windows atau membatasi OS."

    def __init__(self, args):
        super().__init__(args)
        self.stop = threading.Event()

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.stop.set()

    def SvcDoRun(self):
        config = Path(os.getenv("PROGRAMDATA", "C:/ProgramData")) / "LabAccess" / "agent.dpapi"
        try:
            run(config, self.stop)
        except Exception:
            servicemanager.LogErrorMsg("LabAccess Agent gagal; periksa konfigurasi/ACL/identitas DPAPI. Tidak ada credential dicatat.")
            raise


if __name__ == "__main__":
    win32serviceutil.HandleCommandLine(LabAccessAgentService)
