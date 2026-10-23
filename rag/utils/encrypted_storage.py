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
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
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

import logging
from common.crypto_utils import CryptoUtil
# from common.decorator import singleton

class EncryptedStorageWrapper:
    """Encrypted storage wrapper that wraps existing storage implementations to provide transparent encryption"""
    
    def __init__(self, storage_impl, algorithm="aes-256-cbc", key=None, iv=None):
        """
        Initialize encrypted storage wrapper
        
        Args:
            storage_impl: Original storage implementation instance
            algorithm: Encryption algorithm, default is aes-256-cbc
            key: Encryption key, uses RAGFLOW_CRYPTO_KEY environment variable if None
            iv: Initialization vector, automatically generated if None
        """
        self.storage_impl = storage_impl
        self.crypto = CryptoUtil(algorithm=algorithm, key=key, iv=iv)
        self.encryption_enabled = True
        
        # Check if storage implementation has required methods
        # todo: Consider abstracting a storage base class to ensure these methods exist
        required_methods = ["put", "get", "rm", "obj_exist", "health"]
        for method in required_methods:
            if not hasattr(storage_impl, method):
                raise AttributeError(f"Storage implementation missing required method: {method}")
                
        _lineaje_payload = f"EncryptedStorageWrapper initialized with algorithm: {algorithm}"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EncryptedStorageWrapper.__init__).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:df2bf13714eb5910bc1502b7a8e118077c4f6f0c0bbc42e02cb32232841124af'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:df2bf13714eb5910bc1502b7a8e118077c4f6f0c0bbc42e02cb32232841124af', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 45, 'function': 'EncryptedStorageWrapper.__init__'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 45, 'function': '__init__', 'agent_name': 'EncryptedStorageWrapper', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
    
    def put(self, bucket, fnm, binary, tenant_id=None):
        """
        Encrypt and store data
        
        Args:
            bucket: Bucket name
            fnm: File name
            binary: Original binary data
            tenant_id: Tenant ID (optional)
            
        Returns:
            Storage result
        """
        if not self.encryption_enabled:
            return self.storage_impl.put(bucket, fnm, binary, tenant_id)
            
        try:
            encrypted_binary = self.crypto.encrypt(binary)
            
            return self.storage_impl.put(bucket, fnm, encrypted_binary, tenant_id)
        except Exception as e:
            _lineaje_payload = f"Failed to encrypt and store data: {bucket}/{fnm}, error: {str(e)}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EncryptedStorageWrapper.put).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:80678942654230260aa5e98d564e6e1883a6a12e012c106f63d2c3407d42230d'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:80678942654230260aa5e98d564e6e1883a6a12e012c106f63d2c3407d42230d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 68, 'function': 'EncryptedStorageWrapper.put'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 68, 'function': 'put', 'agent_name': 'EncryptedStorageWrapper', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            raise
    
    def get(self, bucket, fnm, tenant_id=None):
        """
        Retrieve and decrypt data
        
        Args:
            bucket: Bucket name
            fnm: File name
            tenant_id: Tenant ID (optional)
            
        Returns:
            Decrypted binary data
        """
        try:
            # Get encrypted data
            encrypted_binary = self.storage_impl.get(bucket, fnm, tenant_id)
            
            if encrypted_binary is None:
                return None
                
            if not self.encryption_enabled:
                # LINEAJE: runtime guardrail checks `encrypted_binary` as it flows from the agent to the user interface, before it leaves the application (in EncryptedStorageWrapper.get).
                #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
                #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `encrypted_binary` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
                #   Do not remove without review. site_id='site:sha256:1fa3fe18b917a899d5c99de56817475b4b46b9b32006ca0763fa1203c102a470'
                _gr_client = _lineaje_load_gr_client()
                _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:1fa3fe18b917a899d5c99de56817475b4b46b9b32006ca0763fa1203c102a470', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 91, 'function': 'EncryptedStorageWrapper.get'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 91, 'function': 'get', 'agent_name': 'EncryptedStorageWrapper', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
                try:
                    encrypted_binary = _gr_client.enforce(_gr_site, encrypted_binary, content_type='text/plain')
                except _gr_client.GuardrailUnavailableError:
                    pass
                except PermissionError:
                    pass
                return encrypted_binary
                
            # Decrypt data
            decrypted_binary = self.crypto.decrypt(encrypted_binary)
            # LINEAJE: runtime guardrail checks `decrypted_binary` as it flows from the agent to the user interface, before it leaves the application (in EncryptedStorageWrapper.get).
            #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `decrypted_binary` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:9084e15a487db16370db216df31c38f1ba9b6f3939f7f3eb67c169434cd0a10e'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:9084e15a487db16370db216df31c38f1ba9b6f3939f7f3eb67c169434cd0a10e', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 95, 'function': 'EncryptedStorageWrapper.get'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 95, 'function': 'get', 'agent_name': 'EncryptedStorageWrapper', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                decrypted_binary = _gr_client.enforce(_gr_site, decrypted_binary, content_type='text/plain')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            return decrypted_binary
            
        except Exception as e:
            _lineaje_payload = f"Failed to get and decrypt data: {bucket}/{fnm}, error: {str(e)}"
            # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EncryptedStorageWrapper.get).
            #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
            #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
            #   Do not remove without review. site_id='site:sha256:952f313b8055e5d9bb77c51ab2102382ca6e8726774df0eee63ba58e1ebcd93b'
            _gr_client = _lineaje_load_gr_client()
            _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:952f313b8055e5d9bb77c51ab2102382ca6e8726774df0eee63ba58e1ebcd93b', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 98, 'function': 'EncryptedStorageWrapper.get'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 98, 'function': 'get', 'agent_name': 'EncryptedStorageWrapper', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
            try:
                _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
            except _gr_client.GuardrailUnavailableError:
                pass
            except PermissionError:
                pass
            logging.exception(_lineaje_payload)
            raise
    
    def rm(self, bucket, fnm, tenant_id=None):
        """
        Delete data (same as original storage implementation, no decryption needed)
        
        Args:
            bucket: Bucket name
            fnm: File name
            tenant_id: Tenant ID (optional)
            
        Returns:
            Deletion result
        """
        return self.storage_impl.rm(bucket, fnm, tenant_id)
    
    def obj_exist(self, bucket, fnm, tenant_id=None):
        """
        Check if object exists (same as original storage implementation, no decryption needed)
        
        Args:
            bucket: Bucket name
            fnm: File name
            tenant_id: Tenant ID (optional)
            
        Returns:
            Whether the object exists
        """
        return self.storage_impl.obj_exist(bucket, fnm, tenant_id)
    
    def health(self):
        """
        Health check (uses the original storage implementation's method)
        
        Returns:
            Health check result
        """
        return self.storage_impl.health()
    
    def bucket_exists(self, bucket):
        """
        Check if bucket exists (if the original storage implementation has this method)
        
        Args:
            bucket: Bucket name
            
        Returns:
            Whether the bucket exists
        """
        if hasattr(self.storage_impl, "bucket_exists"):
            return self.storage_impl.bucket_exists(bucket)
        return False
    
    def get_presigned_url(self, bucket, fnm, expires, tenant_id=None):
        """
        Get presigned URL (if the original storage implementation has this method)
        
        Args:
            bucket: Bucket name
            fnm: File name
            expires: Expiration time
            tenant_id: Tenant ID (optional)
            
        Returns:
            Presigned URL
        """
        if hasattr(self.storage_impl, "get_presigned_url"):
            return self.storage_impl.get_presigned_url(bucket, fnm, expires, tenant_id)
        return None
    
    def scan(self, bucket, fnm, tenant_id=None):
        """
        Scan objects (if the original storage implementation has this method)
        
        Args:
            bucket: Bucket name
            fnm: File name prefix
            tenant_id: Tenant ID (optional)
            
        Returns:
            Scan results
        """
        if hasattr(self.storage_impl, "scan"):
            return self.storage_impl.scan(bucket, fnm, tenant_id)
        return None
    
    def copy(self, src_bucket, src_path, dest_bucket, dest_path):
        """
        Copy object (if the original storage implementation has this method)
        
        Args:
            src_bucket: Source bucket name
            src_path: Source file path
            dest_bucket: Destination bucket name
            dest_path: Destination file path
            
        Returns:
            Copy result
        """
        if hasattr(self.storage_impl, "copy"):
            return self.storage_impl.copy(src_bucket, src_path, dest_bucket, dest_path)
        return False
    
    def move(self, src_bucket, src_path, dest_bucket, dest_path):
        """
        Move object (if the original storage implementation has this method)
        
        Args:
            src_bucket: Source bucket name
            src_path: Source file path
            dest_bucket: Destination bucket name
            dest_path: Destination file path
            
        Returns:
            Move result
        """
        if hasattr(self.storage_impl, "move"):
            return self.storage_impl.move(src_bucket, src_path, dest_bucket, dest_path)
        return False
    
    def remove_bucket(self, bucket):
        """
        Remove bucket (if the original storage implementation has this method)
        
        Args:
            bucket: Bucket name
            
        Returns:
            Remove result
        """
        if hasattr(self.storage_impl, "remove_bucket"):
            return self.storage_impl.remove_bucket(bucket)
        return False
    
    def enable_encryption(self):
        """Enable encryption"""
        self.encryption_enabled = True
        _lineaje_payload = "Encryption enabled"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EncryptedStorageWrapper.enable_encryption).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:2010fba5a398a66dcbf65f6ee5486221ecab058512e2687ad1344a8082740ebe'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:2010fba5a398a66dcbf65f6ee5486221ecab058512e2687ad1344a8082740ebe', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 236, 'function': 'EncryptedStorageWrapper.enable_encryption'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 236, 'function': 'enable_encryption', 'agent_name': 'EncryptedStorageWrapper', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
    
    def disable_encryption(self):
        """Disable encryption"""
        self.encryption_enabled = False
        _lineaje_payload = "Encryption disabled"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in EncryptedStorageWrapper.disable_encryption).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:76f1e401ca2527b826e819cabf1a4808306c1f2d6f82c962b87bfbb46ff68b2d'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:76f1e401ca2527b826e819cabf1a4808306c1f2d6f82c962b87bfbb46ff68b2d', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 241, 'function': 'EncryptedStorageWrapper.disable_encryption'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 241, 'function': 'disable_encryption', 'agent_name': 'EncryptedStorageWrapper', 'agent_name_source': 'inferred_from_class', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)

# Create singleton wrapper function
def create_encrypted_storage(storage_impl, algorithm=None, key=None, encryption_enabled=True):
    """
    Create singleton instance of encrypted storage wrapper
    
    Args:
        storage_impl: Original storage implementation instance
        algorithm: Encryption algorithm, uses environment variable RAGFLOW_CRYPTO_ALGORITHM or default if None
        key: Encryption key, uses environment variable RAGFLOW_CRYPTO_KEY if None
        encryption_enabled: Whether to enable encryption functionality
        
    Returns:
        Encrypted storage wrapper instance
    """
    wrapper = EncryptedStorageWrapper(storage_impl, algorithm=algorithm, key=key)
    
    wrapper.encryption_enabled = encryption_enabled
    
    if encryption_enabled:
        _lineaje_payload = "Encryption enabled in storage wrapper"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in create_encrypted_storage).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:e2dbbe24bfb7d03580ddbcf8806430948a65f5b22fd75e650c6f83ad64612fbe'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:e2dbbe24bfb7d03580ddbcf8806430948a65f5b22fd75e650c6f83ad64612fbe', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 262, 'function': 'create_encrypted_storage'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 262, 'function': 'create_encrypted_storage', 'agent_name': 'create_encrypted_storage', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
    else:
        _lineaje_payload = "Encryption disabled in storage wrapper"
        # LINEAJE: runtime guardrail checks `_lineaje_payload` as it flows from the agent to the application log, before it is written to the log (in create_encrypted_storage).
        #   Detected: this statement moves data from the agent to the application log with no runtime policy check (detection confidence: high).
        #   Decision: the Guardrail evaluates AI_DAT_SEC_010; sensitive values in `_lineaje_payload` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
        #   Do not remove without review. site_id='site:sha256:7dc3f5779c6b058fdd2eaf01ca2c2f4236140d8b8f6e3587bac8a5b5dcb7678a'
        _gr_client = _lineaje_load_gr_client()
        _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:7dc3f5779c6b058fdd2eaf01ca2c2f4236140d8b8f6e3587bac8a5b5dcb7678a', phase='log_emit', boundary={'source': 'log', 'sink': 'log'}, fail_mode='BLOCK', source_type='agent', destination_type='log', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 264, 'function': 'create_encrypted_storage'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 264, 'function': 'create_encrypted_storage', 'agent_name': 'create_encrypted_storage', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
        try:
            _lineaje_payload = _gr_client.enforce(_gr_site, _lineaje_payload, content_type='application/json')
        except _gr_client.GuardrailUnavailableError:
            pass
        except PermissionError:
            pass
        logging.info(_lineaje_payload)
    
    # LINEAJE: runtime guardrail checks `wrapper` as it flows from the agent to the user interface, before it leaves the application (in create_encrypted_storage).
    #   Detected: this statement moves data from the agent to the user interface with no runtime policy check (detection confidence: high).
    #   Decision: the Guardrail evaluates AI_DAT_SEC_012; sensitive values in `wrapper` are masked in place; a policy violation stops the call (fail_mode=BLOCK). If the Guardrail is unreachable, the call continues unchanged.
    #   Do not remove without review. site_id='site:sha256:994326694f1dc480accef7ba6ab719c8580c35b6f5c19ce9219bef311a539be4'
    _gr_client = _lineaje_load_gr_client()
    _gr_site = _gr_client.SiteDescriptor(site_id='site:sha256:994326694f1dc480accef7ba6ab719c8580c35b6f5c19ce9219bef311a539be4', phase='data_egress', boundary={'source': 'agent_message', 'sink': 'user_interface'}, fail_mode='BLOCK', source_type='agent', destination_type='user_interface', project='tree', organization='', project_name='ragflow', project_version='main', project_branch='main', components={'identity': {'app': {'name': 'ragflow', 'version': 'main', 'purl': 'pkg:github/anaghatestuser/ragflow@main?commit-id=427e0540cab683a591a5f4a65a0b38bf9ee008b7&commit-time=2025-12-25%2003%3A23%3A51%20%2B0000&build_file=pyproject.toml&repo_strategy=single-repo'}}, 'invocation': {'file': 'rag/utils/encrypted_storage.py', 'line': 266, 'function': 'create_encrypted_storage'}, 'file': 'rag/utils/encrypted_storage.py', 'line': 266, 'function': 'create_encrypted_storage', 'agent_name': 'create_encrypted_storage', 'agent_name_source': 'inferred_from_function', 'not_on_graph': True})
    try:
        wrapper = _gr_client.enforce(_gr_site, wrapper, content_type='text/plain')
    except _gr_client.GuardrailUnavailableError:
        pass
    except PermissionError:
        pass
    return wrapper
