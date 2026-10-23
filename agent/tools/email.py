# Copyright (c) Lineaje, Inc. All rights reserved.
# Lineaje UnifAI guardrail  version=2.0.0-alpha
def _lineaje_load_gr_client():
    """Lineaje-added: load gr_stub_client.py without a pip dependency (missing / broken: a pass-through client)."""
    import sys as _s, importlib.util as _ilu
    from pathlib import Path as _P
    n = "_lineaje_gr_stub_client"
    if n in _s.modules: return _s.modules[n]
    try:
        h = _P(__file__).resolve().parent
        _cand = next((d / "gr_stub_client.py" for d in [h, *h.parents][:8] if (d / "gr_stub_client.py").is_file()), h / "gr_stub_client.py")
        _spec = _ilu.spec_from_file_location(n, _cand)
        _s.modules[n] = _m = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_m); return _m
    except Exception:
        _s.modules.pop(n, None)
        return type('_lineaje_gr_unavailable', (), {'STUB_API': 999999, 'GuardrailUnavailableError': type('GuardrailUnavailableError', (PermissionError,), {}), 'SiteDescriptor': staticmethod(lambda *a, **k: None), 'new_interaction_id': staticmethod(lambda *a, **k: None), 'enforce': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_request': staticmethod(lambda _s, _p, *a, **k: _p), 'enforce_reply': staticmethod(lambda _s, _p, *a, **k: _p)})

#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
import os
import time
from abc import ABC
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr

from agent.tools.base import ToolParamBase, ToolBase, ToolMeta
from common.connection_utils import timeout


class EmailParam(ToolParamBase):
    """
    Define the Email component parameters.
    """
    def __init__(self):
        self.meta:ToolMeta = {
            "name": "email",
            "description": "The email is a method of electronic communication for sending and receiving information through the Internet. This tool helps users to send emails to one person or to multiple recipients with support for CC, BCC, file attachments, and markdown-to-HTML conversion.",
            "parameters": {
                "to_email": {
                    "type": "string",
                    "description": "The target email address.",
                    "default": "{sys.query}",
                    "required": True
                },
                "cc_email": {
                    "type": "string",
                    "description": "The other email addresses needs to be send to. Comma splited.",
                    "default": "",
                    "required": False
                },
                "content": {
                    "type": "string",
                    "description": "The content of the email.",
                    "default": "",
                    "required": False
                },
                "subject": {
                    "type": "string",
                    "description": "The subject/title of the email.",
                    "default": "",
                    "required": False
                }
            }
        }
        super().__init__()
        # Fixed configuration parameters
        self.smtp_server = ""  # SMTP server address
        self.smtp_port = 465  # SMTP port
        self.email = ""  # Sender email
        self.password = ""  # Email authorization code
        self.sender_name = ""  # Sender name

    def check(self):
        # Check required parameters
        self.check_empty(self.smtp_server, "SMTP Server")
        self.check_empty(self.email, "Email")
        self.check_empty(self.password, "Password")
        self.check_empty(self.sender_name, "Sender Name")

    def get_input_form(self) -> dict[str, dict]:
        return {
            "to_email": {
                "name": "To ",
                "type": "line"
            },
            "subject": {
                "name": "Subject",
                "type": "line",
                "optional": True
            },
            "cc_email": {
                "name": "CC To",
                "type": "line",
                "optional": True
            },
        }

class Email(ToolBase, ABC):
    component_name = "Email"

    @timeout(int(os.environ.get("COMPONENT_EXEC_TIMEOUT", 60)))
    def _invoke(self, **kwargs):
        if self.check_if_canceled("Email processing"):
            return

        if not kwargs.get("to_email"):
            self.set_output("success", False)
            return ""

        last_e = ""
        for _ in range(self._param.max_retries+1):
            if self.check_if_canceled("Email processing"):
                return

            try:
                # Parse JSON string passed from upstream
                email_data = kwargs

                # Validate required fields
                if "to_email" not in email_data:
                    self.set_output("_ERROR", "Missing required field: to_email")
                    self.set_output("success", False)
                    return False

                # Create email object
                msg = MIMEMultipart('alternative')

                # Properly handle sender name encoding
                msg['From'] = formataddr((str(Header(self._param.sender_name,'utf-8')), self._param.email))
                msg['To'] = email_data["to_email"]
                if email_data.get("cc_email"):
                    msg['Cc'] = email_data["cc_email"]
                msg['Subject'] = Header(email_data.get("subject", "No Subject"), 'utf-8').encode()

                # Use content from email_data or default content
                email_content = email_data.get("content", "No content provided")
                # msg.attach(MIMEText(email_content, 'plain', 'utf-8'))
                msg.attach(MIMEText(email_content, 'html', 'utf-8'))

                # Connect to SMTP server and send
                _lineaje_payload = f"Connecting to SMTP server {self._param.smtp_server}:{self._param.smtp_port}"
                # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:70493c62edb176df2c5620050164061d2fb64c2621a3365df6d623cf5c875ea7'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:70493c62edb176df2c5620050164061d2fb64c2621a3365df6d623cf5c875ea7', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 142, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 142, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.info(_lineaje_payload)

                if self.check_if_canceled("Email processing"):
                    return

                context = smtplib.ssl.create_default_context()
                with smtplib.SMTP(self._param.smtp_server, self._param.smtp_port) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    # Login
                    _lineaje_payload = f"Attempting to login with email: {self._param.email}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:e1c01fc2a0df8cee3aa41554e27420f6427c69c8ca691c40c538b267fdaaea6b'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e1c01fc2a0df8cee3aa41554e27420f6427c69c8ca691c40c538b267fdaaea6b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 153, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 153, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)
                    server.login(self._param.email, self._param.password)

                    # Get all recipient list
                    recipients = [email_data["to_email"]]
                    if email_data.get("cc_email"):
                        recipients.extend(email_data["cc_email"].split(','))

                    # Send email
                    _lineaje_payload = f"Sending email to recipients: {recipients}"
                    # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                    #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                    #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                    #   Do not remove without review. site_id='site:sha256:e70c0e310b4049ca5562d5ff1e209046fed37f3322415132e2743f280398542a'
                    _gr_client = _lineaje_load_gr_client()
                    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e70c0e310b4049ca5562d5ff1e209046fed37f3322415132e2743f280398542a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 162, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 162, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                    try:
                        _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                    except _gr_client.GuardrailUnavailableError:
                        pass
                    except PermissionError:
                        pass
                    logging.info(_lineaje_payload)

                    if self.check_if_canceled("Email processing"):
                        return

                    try:
                        server.send_message(msg, self._param.email, recipients)
                        success = True
                    except Exception as e:
                        _lineaje_payload = f"Error during send_message: {str(e)}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:55afcc878de22bf933d0a38349f8c117b0782830ab7b2c0a23a76ef6a4ea2dff'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:55afcc878de22bf933d0a38349f8c117b0782830ab7b2c0a23a76ef6a4ea2dff', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 171, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 171, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.error(_lineaje_payload)
                        # Try alternative method
                        server.sendmail(self._param.email, recipients, msg.as_string())
                        success = True

                    try:
                        server.quit()
                    except Exception as e:
                        # Ignore errors when closing connection
                        _lineaje_payload = f"Non-fatal error during connection close: {str(e)}"
                        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                        #   Do not remove without review. site_id='site:sha256:4221bf8cf7c79aea4c83f9fad3c3f26549e3d996ea217b892cf3a1c1f0810481'
                        _gr_client = _lineaje_load_gr_client()
                        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:4221bf8cf7c79aea4c83f9fad3c3f26549e3d996ea217b892cf3a1c1f0810481', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 180, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 180, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                        try:
                            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
                        except _gr_client.GuardrailUnavailableError:
                            pass
                        except PermissionError:
                            pass
                        logging.warning(_lineaje_payload)

                self.set_output("success", success)
                # LINEAJE: runtime guardrail checks `success` as it flows from the agent to the user interface, before it leaves the application (in Email._invoke).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `success` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:b987d5f0fa79b06407415b2760b60a5f0c41fbc564b2fc60fdf2af7c182d4140'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:b987d5f0fa79b06407415b2760b60a5f0c41fbc564b2fc60fdf2af7c182d4140', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 183, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 183, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    success = _gr_client.enforce(_gr_site, success, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return success

            except json.JSONDecodeError:
                error_msg = "Invalid JSON format in input"
                # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:523bf6f67302f6a3d0c4f44437fcfa2f8e3bc86689b951782a6240046e1ee0b3'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:523bf6f67302f6a3d0c4f44437fcfa2f8e3bc86689b951782a6240046e1ee0b3', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 187, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 187, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(error_msg)
                self.set_output("_ERROR", error_msg)
                self.set_output("success", False)
                return False

            except smtplib.SMTPAuthenticationError:
                error_msg = "SMTP Authentication failed. Please check your email and authorization code."
                # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:e5e895299f6fd1964a6501746a4ffa88a7345ed87ff55d01f58116b6f69c9e13'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e5e895299f6fd1964a6501746a4ffa88a7345ed87ff55d01f58116b6f69c9e13', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 194, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 194, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(error_msg)
                self.set_output("_ERROR", error_msg)
                self.set_output("success", False)
                return False

            except smtplib.SMTPConnectError:
                error_msg = f"Failed to connect to SMTP server {self._param.smtp_server}:{self._param.smtp_port}"
                # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:c954334be4a3750ab7c2f54e236a4541fe860091942490fe492fe740a489f435'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:c954334be4a3750ab7c2f54e236a4541fe860091942490fe492fe740a489f435', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 201, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 201, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(error_msg)
                last_e = error_msg
                time.sleep(self._param.delay_after_error)

            except smtplib.SMTPException as e:
                error_msg = f"SMTP error occurred: {str(e)}"
                # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:f99d60632f867ab2040967c52b458b5bde769f0762eb09e6139256177b13b54f'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:f99d60632f867ab2040967c52b458b5bde769f0762eb09e6139256177b13b54f', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 207, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 207, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(error_msg)
                last_e = error_msg
                time.sleep(self._param.delay_after_error)

            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                # LINEAJE: runtime guardrail checks `error_msg` as it flows from the agent to the application log, before it is written to the log (in Email._invoke).
                #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `error_msg` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:519f98733995c540c640d71274d9b96c60584eecb3be6dba42479391efc2c822'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:519f98733995c540c640d71274d9b96c60584eecb3be6dba42479391efc2c822', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='0.22.1', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'agent/tools/email.py', 'line': 213, 'function': 'Email._invoke'}, 'file': 'agent/tools/email.py', 'line': 213, 'function': '_invoke', 'agent_name': 'Email', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    error_msg = _gr_client.enforce(_gr_site, error_msg, content_type='application/json')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                logging.error(error_msg)
                self.set_output("_ERROR", error_msg)
                self.set_output("success", False)
                return False

        if last_e:
            self.set_output("_ERROR", str(last_e))
            return False

        assert False, self.output()

    def thoughts(self) -> str:
        inputs = self.get_input()
        return """
To: {}
Subject: {}
Your email is on its way—sit tight!
""".format(inputs.get("to_email", "-_-!"), inputs.get("subject", "-_-!"))
