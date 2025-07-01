import html
from jinja2 import Environment, FileSystemLoader
import os


class ReportGenerator:
    @staticmethod
    def generate_html_report(data, base_url):
        severity_colors = {
            "low": "#ADD8E6",  # Light Blue
            "medium": "#ffab40",  # Yellow
            "high": "#8B0000",  # Red Brown
            "critical": "#FF0000",  # Red
        }

        def sanitize_payload(payload):
            return html.escape(str(payload)) if payload else ""

        def get_recommendations(metadata):
            return metadata.get("remediation", "No recommendations provided.")

        detected_vuln_types = set()
        total_requests = sum(
            item.get("counter", 0) for item in data
        )
        total_vulnerabilities = len(data)

        vulnerabilities = []
        for item in data:
            for vuln_type, details_list in item.items():
                if vuln_type == "counter":
                    continue
                for details in details_list:
                    metadata = details.get("metadata")
                    if metadata:
                        detected_vuln_types.add(metadata["test_name"])
                        severity = metadata.get("severity", "").lower()
                        severity_color = severity_colors.get(severity, "#f8f8f8")
                        vulnerability = {
                            "test_name": html.escape(metadata["test_name"]),
                            "severity": html.escape(metadata["severity"]),
                            "description": html.escape(metadata["short_description"]),
                            "cwe": html.escape(metadata["CWE"]),
                            "cvss": html.escape(str(metadata["cvss"])),
                            "remediation": get_recommendations(metadata),
                            "severity_color": severity_color,
                            "request": sanitize_payload(details.get("request")),
                            "response": sanitize_payload(details.get("response")),
                            "payload": sanitize_payload(details.get("payload")),
                            "token": sanitize_payload(details.get("token")),
                            "parameter": sanitize_payload(details.get("parameter")),
                            "page_url": sanitize_payload(details.get("page_url")),
                            "endpoint": sanitize_payload(details.get("endpoint")),
                            "popup_detected": sanitize_payload(details.get("popup_detected")),
                            "filename": sanitize_payload(details.get("filename")),
                            "method": sanitize_payload(details.get("method")),
                        }
                        print(vulnerability)
                        vulnerabilities.append(vulnerability)

        template_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template("scan/report/template/html_template.html")

        html_report = template.render(
            base_url=base_url,
            total_requests=total_requests,
            total_vulnerabilities=total_vulnerabilities,
            vulnerabilities=vulnerabilities,
        )

        return html_report, total_vulnerabilities
