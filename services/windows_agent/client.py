"""Adapter UI ke named pipe lokal; tidak memberi UI secret perangkat milik agent."""
import base64
from .bridge import pipe_request


class AgentApi:
    def __init__(self, pipe_name):
        self.pipe_name = pipe_name
        self.device = pipe_request(pipe_name, {"op": "metadata"})
        self.token, self.url, self.ca = "", "agent-local", True

    def request(self, method, path, *, raw=False, **kwargs):
        if raw:
            raise RuntimeError("Operasi binary tidak diizinkan pada agent mahasiswa")
        data = {"method": method, "path": path}
        if "json" in kwargs:
            data["json"] = kwargs["json"]
        if "files" in kwargs:
            data["frames"] = [base64.b64encode(item[1][1]).decode() for item in kwargs["files"]]
            data["data"] = kwargs.get("data", {})
        return pipe_request(self.pipe_name, data)
