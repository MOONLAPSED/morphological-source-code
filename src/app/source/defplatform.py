import os
import sys
import re
import platform
import ctypes
from enum import IntFlag, auto
from typing import Dict, Any, List, Optional, Tuple


# Platform detection constants
IS_WINDOWS = sys.platform == 'win32'
IS_LINUX = sys.platform.startswith('linux')
IS_MACOS = sys.platform == 'darwin'
IS_POSIX = os.name == 'posix'
IS_64BIT = sys.maxsize > 2**32


class ProcessorFeatures(IntFlag):
    """Extensible processor feature detection."""
    BASIC = auto()
    SSE = auto()
    SSE2 = auto()
    SSE3 = auto()
    SSSE3 = auto()
    SSE41 = auto()
    SSE42 = auto()
    AVX = auto()
    AVX2 = auto()
    AVX512F = auto()  # Foundation
    AVX512BW = auto()  # Byte and Word
    AVX512CD = auto()  # Conflict Detection
    AVX512DQ = auto()  # Doubleword and Quadword
    AVX512VL = auto()  # Vector Length Extensions
    NEON = auto()
    SVE = auto()
    SVE2 = auto()
    RVV = auto()  # RISC-V Vector Extensions
    AMX = auto()  # Advanced Matrix Extensions
    FMA = auto()  # Fused Multiply-Add
    
    @classmethod
    def detect_features(cls) -> 'ProcessorFeatures':
        """Detect available processor features across platforms."""
        features = cls.BASIC
        
        # Get the machine architecture
        machine = platform.machine().lower()
        
        try:
            # Handle x86/x64 processors
            if machine in ('x86_64', 'amd64', 'x86', 'i386', 'i686'):
                features = cls._detect_x86_features()
            
            # Handle ARM processors
            elif machine.startswith('arm') or machine.startswith('aarch'):
                features = cls._detect_arm_features()
                
            # Handle RISC-V processors
            elif machine.startswith('riscv'):
                features = cls._detect_riscv_features()
                
        except Exception as e:
            print(f"Warning: Error detecting processor features: {e}")
            # Fall back to basic features
            
        return features
    
    @classmethod
    def _detect_x86_features(cls) -> 'ProcessorFeatures':
        """Detect x86/x64 specific processor features."""
        features = cls.BASIC
        
        # Windows-specific detection
        if IS_WINDOWS:
            features |= cls._detect_x86_features_windows()
        
        # Linux-specific detection
        elif IS_LINUX:
            features |= cls._detect_x86_features_linux()
            
        # macOS-specific detection
        elif IS_MACOS:
            features |= cls._detect_x86_features_macos()
            
        return features
    
    @classmethod
    def _detect_x86_features_windows(cls) -> 'ProcessorFeatures':
        """Detect x86/x64 features on Windows."""
        features = cls.BASIC
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r'HARDWARE\DESCRIPTION\System\CentralProcessor\0')
            
            # Get processor name
            identifier = winreg.QueryValueEx(key, 'ProcessorNameString')[0].lower()
            
            # Use Windows API to get CPUID information for more reliable detection
            features |= cls._parse_cpu_features_from_name(identifier)
            
            # For more accurate feature detection, use Windows-specific feature detection
            try:
                # Check for specific CPU features using IsProcessorFeaturePresent
                # https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-isprocessorfeaturepresent
                kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                
                # Define Windows processor feature constants
                PF_XMMI_INSTRUCTIONS_AVAILABLE = 6       # SSE
                PF_XMMI64_INSTRUCTIONS_AVAILABLE = 10    # SSE2
                PF_SSE3_INSTRUCTIONS_AVAILABLE = 13      # SSE3
                PF_SSSE3_INSTRUCTIONS_AVAILABLE = 36     # SSSE3
                PF_SSE4_1_INSTRUCTIONS_AVAILABLE = 37    # SSE4.1
                PF_SSE4_2_INSTRUCTIONS_AVAILABLE = 38    # SSE4.2
                PF_AVX_INSTRUCTIONS_AVAILABLE = 39       # AVX
                PF_AVX2_INSTRUCTIONS_AVAILABLE = 40      # AVX2
                PF_AVX512F_INSTRUCTIONS_AVAILABLE = 41   # AVX-512F
                
                # Check each feature
                if kernel32.IsProcessorFeaturePresent(PF_XMMI_INSTRUCTIONS_AVAILABLE):
                    features |= cls.SSE
                if kernel32.IsProcessorFeaturePresent(PF_XMMI64_INSTRUCTIONS_AVAILABLE):
                    features |= cls.SSE2
                if kernel32.IsProcessorFeaturePresent(PF_SSE3_INSTRUCTIONS_AVAILABLE):
                    features |= cls.SSE3
                if kernel32.IsProcessorFeaturePresent(PF_SSSE3_INSTRUCTIONS_AVAILABLE):
                    features |= cls.SSSE3
                if kernel32.IsProcessorFeaturePresent(PF_SSE4_1_INSTRUCTIONS_AVAILABLE):
                    features |= cls.SSE41
                if kernel32.IsProcessorFeaturePresent(PF_SSE4_2_INSTRUCTIONS_AVAILABLE):
                    features |= cls.SSE42
                if kernel32.IsProcessorFeaturePresent(PF_AVX_INSTRUCTIONS_AVAILABLE):
                    features |= cls.AVX
                if kernel32.IsProcessorFeaturePresent(PF_AVX2_INSTRUCTIONS_AVAILABLE):
                    features |= cls.AVX2
                
                # Note: Some Windows versions might not define AVX-512 constants
                try:
                    if kernel32.IsProcessorFeaturePresent(PF_AVX512F_INSTRUCTIONS_AVAILABLE):
                        features |= cls.AVX512F
                except Exception:
                    pass
                    
            except Exception as e:
                print(f"Warning: Windows-specific feature detection failed: {e}")
                
        except Exception as e:
            print(f"Warning: Windows registry access failed: {e}")
            
        return features
    
    @classmethod
    def _detect_x86_features_linux(cls) -> 'ProcessorFeatures':
        """Detect x86/x64 features on Linux."""
        features = cls.BASIC
        try:
            # Read CPU flags from /proc/cpuinfo
            with open('/proc/cpuinfo', 'r') as f:
                cpuinfo = f.read().lower()
            
            # Extract the flags line containing CPU feature flags
            flags_match = re.search(r'flags\s+:\s+(.*)', cpuinfo)
            if flags_match:
                flags = flags_match.group(1).split()
                
                # Check for specific flags
                if 'sse' in flags:
                    features |= cls.SSE
                if 'sse2' in flags:
                    features |= cls.SSE2
                if 'sse3' in flags:
                    features |= cls.SSE3
                if 'ssse3' in flags:
                    features |= cls.SSSE3
                if 'sse4_1' in flags:
                    features |= cls.SSE41
                if 'sse4_2' in flags:
                    features |= cls.SSE42
                if 'avx' in flags:
                    features |= cls.AVX
                if 'avx2' in flags:
                    features |= cls.AVX2
                if 'fma' in flags:
                    features |= cls.FMA
                    
                # AVX-512 features
                if 'avx512f' in flags:
                    features |= cls.AVX512F
                if 'avx512bw' in flags:
                    features |= cls.AVX512BW
                if 'avx512cd' in flags:
                    features |= cls.AVX512CD
                if 'avx512dq' in flags:
                    features |= cls.AVX512DQ
                if 'avx512vl' in flags:
                    features |= cls.AVX512VL
                    
            # Get CPU model name for fallback detection
            model_match = re.search(r'model name\s+:\s+(.*)', cpuinfo)
            if model_match:
                model_name = model_match.group(1).lower()
                if features == cls.BASIC:  # Only use as fallback
                    features |= cls._parse_cpu_features_from_name(model_name)
                
        except Exception as e:
            print(f"Warning: Linux CPU feature detection failed: {e}")
            
        return features
    
    @classmethod
    def _detect_x86_features_macos(cls) -> 'ProcessorFeatures':
        """Detect x86/x64 features on macOS."""
        features = cls.BASIC
        try:
            # On macOS, use sysctl to get CPU features
            import subprocess
            
            # Get CPU brand string
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], 
                                   capture_output=True, text=True, check=True)
            cpu_name = result.stdout.strip().lower()
            
            # Get CPU features
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.features'], 
                                   capture_output=True, text=True, check=True)
            cpu_features = result.stdout.strip().upper().split()
            
            # Check for extended features
            try:
                result = subprocess.run(['sysctl', '-n', 'machdep.cpu.leaf7_features'], 
                                      capture_output=True, text=True, check=True)
                leaf7_features = result.stdout.strip().upper().split()
                cpu_features.extend(leaf7_features)
            except subprocess.CalledProcessError:
                pass
                
            # Map features
            if 'SSE' in cpu_features:
                features |= cls.SSE
            if 'SSE2' in cpu_features:
                features |= cls.SSE2
            if 'SSE3' in cpu_features:
                features |= cls.SSE3
            if 'SSSE3' in cpu_features:
                features |= cls.SSSE3
            if 'SSE4.1' in cpu_features:
                features |= cls.SSE41
            if 'SSE4.2' in cpu_features:
                features |= cls.SSE42
            if 'AVX1.0' in cpu_features or 'AVX' in cpu_features:
                features |= cls.AVX
            if 'AVX2' in cpu_features:
                features |= cls.AVX2
            if 'FMA' in cpu_features:
                features |= cls.FMA
                
            # AVX-512 features
            if 'AVX512F' in cpu_features:
                features |= cls.AVX512F
            if 'AVX512BW' in cpu_features:
                features |= cls.AVX512BW
            if 'AVX512CD' in cpu_features:
                features |= cls.AVX512CD
            if 'AVX512DQ' in cpu_features:
                features |= cls.AVX512DQ
            if 'AVX512VL' in cpu_features:
                features |= cls.AVX512VL
                
            # Fallback to CPU name parsing if needed
            if features == cls.BASIC:
                features |= cls._parse_cpu_features_from_name(cpu_name)
                
        except Exception as e:
            print(f"Warning: macOS CPU feature detection failed: {e}")
            
        return features
        
    @classmethod
    def _detect_arm_features(cls) -> 'ProcessorFeatures':
        """Detect ARM specific processor features."""
        features = cls.BASIC
        
        # Windows ARM detection
        if IS_WINDOWS:
            # Limited ARM feature detection on Windows
            # Most Windows ARM devices have NEON
            features |= cls.NEON
            
        # Linux ARM detection
        elif IS_LINUX:
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read().lower()
                
                # Check for NEON
                if 'neon' in cpuinfo or 'asimd' in cpuinfo:
                    features |= cls.NEON
                    
                # Check for SVE
                if 'sve' in cpuinfo:
                    features |= cls.SVE
                    
                # Check for SVE2
                if 'sve2' in cpuinfo:
                    features |= cls.SVE2
            except Exception as e:
                print(f"Warning: ARM feature detection on Linux failed: {e}")
                
        # macOS ARM detection (Apple Silicon)
        elif IS_MACOS:
            # All Apple Silicon chips have NEON
            features |= cls.NEON
            
        return features
    
    @classmethod
    def _detect_riscv_features(cls) -> 'ProcessorFeatures':
        """Detect RISC-V specific processor features."""
        features = cls.BASIC
        
        # RISC-V feature detection on Linux
        if IS_LINUX:
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read().lower()
                
                # Check for RVV (RISC-V Vector Extensions)
                if 'v' in cpuinfo or 'rvv' in cpuinfo:
                    features |= cls.RVV
            except Exception as e:
                print(f"Warning: RISC-V feature detection failed: {e}")
                
        return features
    
    @classmethod
    def _parse_cpu_features_from_name(cls, cpu_name: str) -> 'ProcessorFeatures':
        """Parse CPU features from processor name (fallback method)."""
        features = cls.BASIC
        cpu_name = cpu_name.lower()
        
        # Basic feature detection from CPU name
        if 'sse' in cpu_name:
            features |= cls.SSE
        if 'sse2' in cpu_name:
            features |= cls.SSE2
        if 'sse3' in cpu_name:
            features |= cls.SSE3
        if 'ssse3' in cpu_name:
            features |= cls.SSSE3
        if 'sse4.1' in cpu_name or 'sse4_1' in cpu_name:
            features |= cls.SSE41
        if 'sse4.2' in cpu_name or 'sse4_2' in cpu_name:
            features |= cls.SSE42
        if 'avx' in cpu_name:
            features |= cls.AVX
        if 'avx2' in cpu_name:
            features |= cls.AVX2
        if 'avx-512' in cpu_name or 'avx512' in cpu_name:
            features |= cls.AVX512F
        if 'neon' in cpu_name:
            features |= cls.NEON
        if 'sve' in cpu_name:
            features |= cls.SVE
        if 'amx' in cpu_name:
            features |= cls.AMX
            
        return features
    
    def get_feature_names(self) -> List[str]:
        """Return a list of enabled feature names."""
        names = []
        for feature in ProcessorFeatures:
            if self & feature and feature != ProcessorFeatures.BASIC:
                names.append(feature.name)
        return names
    
    def has_feature(self, feature: 'ProcessorFeatures') -> bool:
        """Check if a specific feature is available."""
        return bool(self & feature)
    
    def __str__(self) -> str:
        """Return a string representation of enabled features."""
        if self == ProcessorFeatures.BASIC:
            return "BASIC"
        return " | ".join(self.get_feature_names())


class VirtualizationType(IntFlag):
    """Types of virtualization environments."""
    NONE = 0
    VMWARE = auto()
    VIRTUALBOX = auto()
    KVM = auto()
    XEN = auto()
    HYPERV = auto()
    PARALLELS = auto()
    QEMU = auto()
    DOCKER = auto()
    LXC = auto()
    PODMAN = auto()
    WSL = auto()  # Windows Subsystem for Linux
    BHYVE = auto()  # FreeBSD Hypervisor
    AWS = auto()
    AZURE = auto()
    GCP = auto()
    
    def __str__(self) -> str:
        """Return a string representation."""
        if self == VirtualizationType.NONE:
            return "None"
        names = []
        for vtype in VirtualizationType:
            if self & vtype and vtype != VirtualizationType.NONE:
                names.append(vtype.name)
        return " | ".join(names)


class PlatformInterface:
    """Abstract base class for platform-specific implementations."""
    
    def __init__(self):
        """Initialize platform interface with common attributes."""
        self.platform_name = self._get_platform_name()
        self.arch = platform.machine()
        self.processor_features = ProcessorFeatures.detect_features()
        
    def _get_platform_name(self) -> str:
        """Get detailed platform name."""
        return f"{platform.system()} {platform.release()}"
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load and return the platform-specific C library."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def get_c_library_symbol(self, library: ctypes.CDLL, symbol_name: str) -> Optional[Any]:
        """Get and return the platform-specific C library symbol."""
        try:
            return getattr(library, symbol_name)
        except AttributeError:
            print(f"Symbol '{symbol_name}' not found in library")
            return None
    
    def get_platform_info(self) -> Dict[str, Any]:
        """Get comprehensive information about the current platform."""
        info = {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
            'python_compiler': platform.python_compiler(),
            'processor_features': str(self.processor_features),
            'is_64bit': IS_64BIT,
        }
        
        # Add virtualization information
        virt_info = self.detect_virtualization()
        info['virtualization'] = {
            'virtualized': virt_info['virtualized'],
            'type': str(virt_info['virt_type']) if virt_info['virtualized'] else "None",
            'confidence': virt_info['confidence'],
            'evidence': virt_info['evidence']
        }
        
        # Add platform-specific information
        self._add_platform_specific_info(info)
        
        return info
    
    def _add_platform_specific_info(self, info: Dict[str, Any]) -> None:
        """Add platform-specific information to the info dictionary."""
        # To be implemented by subclasses
        pass
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get system memory information."""
        raise NotImplementedError("Subclasses must implement this method")
    
    def execute_command(self, command: List[str]) -> Tuple[int, str, str]:
        """Execute a command and return returncode, stdout, and stderr."""
        import subprocess
        try:
            proc = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            return proc.returncode, proc.stdout, proc.stderr
        except Exception as e:
            return -1, "", str(e)
    
    def detect_virtualization(self) -> Dict[str, Any]:
        """Detect if running in a virtualized environment.
        
        Returns:
            Dict with keys:
            - virtualized (bool): Whether virtualization was detected
            - virt_type (VirtualizationType): Type of virtualization detected
            - confidence (float): Confidence level from 0.0 to 1.0
            - evidence (List[str]): List of evidence for virtualization
        """
        result = {
            'virtualized': False,
            'virt_type': VirtualizationType.NONE,
            'confidence': 0.0,
            'evidence': []
        }
        
        # Start with CPU feature-based checks (common across platforms)
        self._detect_virt_via_cpu_features(result)
        
        # Platform-specific detection
        if IS_LINUX:
            self._detect_virtualization_linux(result)
        elif IS_WINDOWS:
            self._detect_virtualization_windows(result)
        elif IS_MACOS:
            self._detect_virtualization_macos(result)
            
        # Cloud platform detection
        self._detect_cloud_provider(result)
        
        # Calculate confidence level based on evidence count
        if result['evidence']:
            # More evidence = higher confidence
            evidence_weight = min(len(result['evidence']) / 3.0, 1.0)
            # Start at 0.6 confidence with any evidence
            result['confidence'] = 0.6 + (0.4 * evidence_weight)
        
        return result
    
    def _detect_virt_via_cpu_features(self, result: Dict[str, Any]) -> None:
        """Detect virtualization via CPU feature anomalies."""
        # Many hypervisors impact CPU feature reporting
        if IS_WINDOWS or IS_LINUX:
            # In real hardware, certain feature combinations are expected
            cpu_features = self.processor_features
            
            # Example: Check for inconsistent feature combinations
            if cpu_features.has_feature(ProcessorFeatures.AVX) and not cpu_features.has_feature(ProcessorFeatures.SSE3):
                result['evidence'].append("Inconsistent CPU feature set detected (AVX without SSE3)")
                result['virtualized'] = True
                
            # Check for CPU name patterns (often modified by hypervisors)
            try:
                if IS_LINUX:
                    with open('/proc/cpuinfo', 'r') as f:
                        cpuinfo = f.read().lower()
                        if 'qemu' in cpuinfo or 'kvm' in cpuinfo:
                            result['evidence'].append("CPU reports QEMU/KVM in model name")
                            result['virtualized'] = True
                            result['virt_type'] |= VirtualizationType.KVM
                elif IS_WINDOWS:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                        r'HARDWARE\DESCRIPTION\System\CentralProcessor\0')
                    cpu_name = winreg.QueryValueEx(key, 'ProcessorNameString')[0].lower()
                    winreg.CloseKey(key)
                    
                    for virt_keyword, virt_type in [
                        ('kvm', VirtualizationType.KVM),
                        ('qemu', VirtualizationType.QEMU),
                        ('virtual', VirtualizationType.HYPERV),  # Generic, but common in Hyper-V
                        ('vmware', VirtualizationType.VMWARE)
                    ]:
                        if virt_keyword in cpu_name:
                            result['evidence'].append(f"CPU reports {virt_keyword} in model name")
                            result['virtualized'] = True
                            result['virt_type'] |= virt_type
            except Exception:
                pass
    
    def _detect_virtualization_linux(self, result: Dict[str, Any]) -> None:
        """Linux-specific virtualization detection."""
        try:
            # Check dmesg for virtualization hints
            returncode, stdout, stderr = self.execute_command(['dmesg'])
            if returncode == 0:
                stdout_lower = stdout.lower()
                
                # Check for various virtualization technologies
                virt_indicators = [
                    ('vmware', VirtualizationType.VMWARE, 'dmesg contains VMware references'),
                    ('virtualbox', VirtualizationType.VIRTUALBOX, 'dmesg contains VirtualBox references'),
                    ('vbox', VirtualizationType.VIRTUALBOX, 'dmesg contains VBox references'),
                    ('kvm', VirtualizationType.KVM, 'dmesg contains KVM references'),
                    ('qemu', VirtualizationType.QEMU, 'dmesg contains QEMU references'),
                    ('xen', VirtualizationType.XEN, 'dmesg contains Xen references'),
                    ('hyper-v', VirtualizationType.HYPERV, 'dmesg contains Hyper-V references'),
                    ('hyperv', VirtualizationType.HYPERV, 'dmesg contains HyperV references'),
                    ('docker', VirtualizationType.DOCKER, 'dmesg contains Docker references'),
                    ('lxc', VirtualizationType.LXC, 'dmesg contains LXC references'),
                    ('container', VirtualizationType.DOCKER, 'dmesg contains container references'),
                    ('wsl', VirtualizationType.WSL, 'dmesg contains WSL references')
                ]
                
                for keyword, virt_type, evidence in virt_indicators:
                    if keyword in stdout_lower:
                        result['virtualized'] = True
                        result['virt_type'] |= virt_type
                        result['evidence'].append(evidence)
            
            # Check for specific virtual files
            virtual_files = [
                ('/sys/hypervisor/type', 'hypervisor type file'),
                ('/proc/xen', 'Xen proc file'),
                ('/proc/self/cgroup', 'cgroups file')
            ]
            
            for vfile, evidence_prefix in virtual_files:
                if os.path.exists(vfile):
                    try:
                        with open(vfile, 'r') as f:
                            content = f.read().lower()
                            evidence = f"{evidence_prefix} exists: {content[:50]}..."
                            result['evidence'].append(evidence)
                            
                            # Set virtualization type based on content
                            if 'xen' in content:
                                result['virtualized'] = True
                                result['virt_type'] |= VirtualizationType.XEN
                            elif 'kvm' in content:
                                result['virtualized'] = True
                                result['virt_type'] |= VirtualizationType.KVM
                            elif 'vmware' in content:
                                result['virtualized'] = True
                                result['virt_type'] |= VirtualizationType.VMWARE
                            elif 'docker' in content or 'lxc' in content:
                                result['virtualized'] = True
                                result['virt_type'] |= VirtualizationType.DOCKER
                            elif 'podman' in content:
                                result['virtualized'] = True
                                result['virt_type'] |= VirtualizationType.PODMAN
                    except Exception:
                        pass
                        
            # Check using systemd-detect-virt if available
            returncode, stdout, stderr = self.execute_command(['systemd-detect-virt'])
            if returncode == 0 and stdout.strip() not in ('none', ''):
                result['virtualized'] = True
                virt_name = stdout.strip().lower()
                result['evidence'].append(f"systemd-detect-virt reports: {virt_name}")
                
                # Map systemd-detect-virt output to VirtualizationType
                virt_mapping = {
                    'kvm': VirtualizationType.KVM,
                    'qemu': VirtualizationType.QEMU,
                    'vmware': VirtualizationType.VMWARE,
                    'microsoft': VirtualizationType.HYPERV,
                    'oracle': VirtualizationType.VIRTUALBOX,
                    'xen': VirtualizationType.XEN,
                    'docker': VirtualizationType.DOCKER,
                    'lxc': VirtualizationType.LXC,
                    'podman': VirtualizationType.PODMAN,
                    'wsl': VirtualizationType.WSL
                }
                
                for key, vtype in virt_mapping.items():
                    if key in virt_name:
                        result['virt_type'] |= vtype
                        break
                        
            # Check DMI info for virtualization clues
            try:
                if os.path.exists('/sys/class/dmi/id/product_name'):
                    with open('/sys/class/dmi/id/product_name', 'r') as f:
                        product = f.read().strip().lower()
                        
                        virt_products = [
                            ('vmware', VirtualizationType.VMWARE, 'VMware product detected'),
                            ('virtualbox', VirtualizationType.VIRTUALBOX, 'VirtualBox product detected'),
                            ('kvm', VirtualizationType.KVM, 'KVM product detected'),
                            ('xen', VirtualizationType.XEN, 'Xen product detected'),
                            ('hyperv', VirtualizationType.HYPERV, 'Hyper-V product detected'),
                            ('qemu', VirtualizationType.QEMU, 'QEMU product detected'),
                            ('parallels', VirtualizationType.PARALLELS, 'Parallels product detected')
                        ]
                        
                        for keyword, virt_type, evidence in virt_products:
                            if keyword in product:
                                result['virtualized'] = True
                                result['virt_type'] |= virt_type
                                result['evidence'].append(f"{evidence}: {product}")
            except Exception:
                pass
                
        except Exception as e:
            result['error'] = str(e)
    
    def _detect_virtualization_windows(self, result: Dict[str, Any]) -> None:
        """Windows-specific virtualization detection."""
        try:
            import winreg
            
            # Check for common registry keys that indicate virtualization
            virt_indicators = [
                (r'SYSTEM\CurrentControlSet\Control\VirtualDeviceDrivers', 
                 VirtualizationType.HYPERV, 'Registry contains virtual device drivers'),
                (r'SYSTEM\CurrentControlSet\Services\VMTools', 
                 VirtualizationType.VMWARE, 'VMware Tools service exists'),
                (r'SYSTEM\CurrentControlSet\Services\VBoxService', 
                 VirtualizationType.VIRTUALBOX, 'VirtualBox service exists'),
                (r'SOFTWARE\VMware, Inc.', 
                 VirtualizationType.VMWARE, 'VMware software registry key exists'),
                (r'SOFTWARE\Oracle\VirtualBox Guest Additions', 
                 VirtualizationType.VIRTUALBOX, 'VirtualBox registry key exists'),
                (r'SOFTWARE\Microsoft\Virtual Machine\Guest', 
                 VirtualizationType.HYPERV, 'Hyper-V guest registry key exists'),
                (r'SYSTEM\HardwareConfig\Current\VIRTRAID', 
                 VirtualizationType.HYPERV, 'Virtual RAID device detected')
            ]
            
            for reg_key, virt_type, evidence in virt_indicators:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key)
                    winreg.CloseKey(key)
                    result['virtualized'] = True
                    result['virt_type'] |= virt_type
                    result['evidence'].append(evidence)
                except FileNotFoundError:
                    # Registry key doesn't exist
                    pass
                except Exception:
                    # Other error opening registry key
                    pass
            
            # Check Windows Management Instrumentation (WMI)
            try:
                import wmi
                w = wmi.WMI()
                
                # Check computer system product details
                for cs in w.Win32_ComputerSystem():
                    model = cs.Model.lower() if cs.Model else ""
                    manufacturer = cs.Manufacturer.lower() if cs.Manufacturer else ""
                    
                    # Check for virtual machine indicators
                    vm_manufacturers = [
                        ('vmware', VirtualizationType.VMWARE, 'VMware detected in WMI system info'),
                        ('virtual', VirtualizationType.HYPERV, 'Virtual machine detected in WMI system info'),
                        ('virtualbox', VirtualizationType.VIRTUALBOX, 'VirtualBox detected in WMI system info'),
                        ('kvm', VirtualizationType.KVM, 'KVM detected in WMI system info'),
                        ('xen', VirtualizationType.XEN, 'Xen detected in WMI system info'),
                        ('parallels', VirtualizationType.PARALLELS, 'Parallels detected in WMI system info')
                    ]
                    
                    for keyword, virt_type, evidence in vm_manufacturers:
                        if keyword in model or keyword in manufacturer:
                            result['virtualized'] = True
                            result['virt_type'] |= virt_type
                            result['evidence'].append(evidence)
                
                # Check for virtual devices
                for disk in w.Win32_DiskDrive():
                    if disk.Model:
                        model = disk.Model.lower()
                        if any(v in model for v in ['vmware', 'virtual', 'vbox']):
                            result['virtualized'] = True
                            if 'vmware' in model:
                                result['virt_type'] |= VirtualizationType.VMWARE
                            elif 'vbox' in model:
                                result['virt_type'] |= VirtualizationType.VIRTUALBOX
                            else:
                                result['virt_type'] |= VirtualizationType.HYPERV
                            result['evidence'].append(f"Virtual disk detected: {disk.Model}")
            except Exception:
                # WMI might not be available or accessible
                pass
                
            # Check for WSL
            try:
                # Check for WSL-specific environment variable
                if os.environ.get('WSL_DISTRO_NAME'):
                    result['virtualized'] = True
                    result['virt_type'] |= VirtualizationType.WSL
                    result['evidence'].append(f"WSL detected via environment variables")
                    
                # Check for WSL-specific path
                wsl_path = r'C:\Windows\System32\wsl.exe'
                if os.path.exists(wsl_path):
                    # This alone doesn't confirm we're in WSL, just that WSL is installed
                    pass
            except Exception:
                pass
                
        except Exception as e:
            result['error'] = str(e)
    
    def _detect_virtualization_macos(self, result: Dict[str, Any]) -> None:
        """macOS-specific virtualization detection."""
        try:
            # Check for common virtual hardware identifiers
            returncode, stdout, stderr = self.execute_command(['system_profiler', 'SPHardwareDataType'])
            if returncode == 0:
                stdout_lower = stdout.lower()
                
                # Check for virtual machine indicators
                vm_indicators = [
                    ('vmware', VirtualizationType.VMWARE, 'VMware hardware detected'),
                    ('virtualbox', VirtualizationType.VIRTUALBOX, 'VirtualBox hardware detected'),
                    ('parallels', VirtualizationType.PARALLELS, 'Parallels hardware detected'),
                    ('qemu', VirtualizationType.QEMU, 'QEMU hardware detected')
                ]
                
                for keyword, virt_type, evidence in vm_indicators:
                    if keyword in stdout_lower:
                        result['virtualized'] = True
                        result['virt_type'] |= virt_type
                        result['evidence'].append(evidence)
            
            # Check for specific virtualization files or directories
            virt_paths = [
                ('/Library/Application Support/VMware Tools', VirtualizationType.VMWARE, 'VMware Tools'),
                ('/Library/Application Support/VirtualBox Guest Additions', VirtualizationType.VIRTUALBOX, 'VirtualBox Additions')
            ]
            
            for path, virt_type, name in virt_paths:
                if os.path.exists(path):
                    result['virtualized'] = True
                    result['virt_type'] |= virt_type
                    result['evidence'].append(f"{name} detected at {path}")
                    
            # Check via ioreg for virtual devices
            returncode, stdout, stderr = self.execute_command(['ioreg', '-l'])
            if returncode == 0:
                stdout_lower = stdout.lower()
                
                for keyword, virt_type, evidence in vm_indicators:
                    if keyword in stdout_lower:
                        result['virtualized'] = True
                        result['virt_type'] |= virt_type
                        result['evidence'].append(f"{evidence} via ioreg")
                        
        except Exception as e:
            result['error'] = str(e)
    
    def _detect_cloud_provider(self, result: Dict[str, Any]) -> None:
        """Detect if running on a cloud provider."""
        # Check for AWS
        try:
            # AWS metadata service
            import urllib.request
            import socket
            
            # Set a short timeout to avoid hanging if metadata service is not available
            socket.setdefaulttimeout(2)
            
            # Try to access AWS metadata service
            req = urllib.request.Request('http://169.254.169.254/latest/meta-data/')
            try:
                with urllib.request.urlopen(req) as response:
                    if response.getcode() == 200:
                        result['virtualized'] = True
                        result['virt_type'] |= VirtualizationType.AWS
                        result['evidence'].append("AWS metadata service accessible")
            except Exception:
                pass
                
            # Check for GCP
            req = urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/',
                                       headers={'Metadata-Flavor': 'Google'})
            try:
                with urllib.request.urlopen(req) as response:
                    if response.getcode() == 200:
                        result['virtualized'] = True
                        result['virt_type'] |= VirtualizationType.GCP
                        result['evidence'].append("GCP metadata service accessible")
            except Exception:
                pass
                
            # Check for Azure
            req = urllib.request.Request('http://169.254.169.254/metadata/instance?api-version=2020-09-01',
                                       headers={'Metadata': 'true'})
            try:
                with urllib.request.urlopen(req) as response:
                    if response.getcode() == 200:
                        result['virtualized'] = True
                        result['virt_type'] |= VirtualizationType.AZURE
                        result['evidence'].append("Azure metadata service accessible")
            except Exception:
                pass
                
        except Exception:
            # Ignore exceptions when checking cloud providers
            pass


class WindowsPlatform(PlatformInterface):
    """Windows-specific platform implementation."""
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load and return the Windows C library."""
        try:
            return ctypes.windll.kernel32
        except Exception as e:
            print(f"Error loading Windows kernel32 library: {e}")
            return None
    
    def _add_platform_specific_info(self, info: Dict[str, Any]) -> None:
        """Add Windows-specific information to the info dictionary."""
        # Add Windows version information
        try:
            import winreg
            
            # Get Windows edition
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                               r'SOFTWARE\Microsoft\Windows NT\CurrentVersion')
            info['windows_edition'] = winreg.QueryValueEx(key, 'EditionID')[0]
            info['product_name'] = winreg.QueryValueEx(key, 'ProductName')[0]
            
            # Get build information
            try:
                info['display_version'] = winreg.QueryValueEx(key, 'DisplayVersion')[0]
            except Exception:
                pass
            
            try:
                info['current_build'] = winreg.QueryValueEx(key, 'CurrentBuild')[0]
                info['ubr'] = winreg.QueryValueEx(key, 'UBR')[0]  # Update Build Revision
            except Exception:
                pass
                
            winreg.CloseKey(key)
            
        except Exception as e:
            info['windows_info_error'] = str(e)
            
        # Get domain information
        try:
            import socket
            info['computer_name'] = socket.gethostname()
            import subprocess
            proc = subprocess.run(['systeminfo', '/fo', 'list'],
                                capture_output=True, text=True, check=False)
            if proc.returncode == 0:
                # Parse the output
                for line in proc.stdout.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if key == 'Domain':
                            info['domain'] = value
                        elif key == 'System Type':
                            info['system_type'] = value
        except Exception as e:
            info['systeminfo_error'] = str(e)
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get Windows memory information."""
        memory_info = {}
        try:
            import ctypes
            
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]
                
            memory_status = MEMORYSTATUSEX()
            memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
            
            memory_info['total_physical'] = memory_status.ullTotalPhys
            memory_info['available_physical'] = memory_status.ullAvailPhys
            memory_info['memory_load_percent'] = memory_status.dwMemoryLoad
            memory_info['total_pagefile'] = memory_status.ullTotalPageFile
            memory_info['available_pagefile'] = memory_status.ullAvailPageFile
            memory_info['total_virtual'] = memory_status.ullTotalVirtual
            memory_info['available_virtual'] = memory_status.ullAvailVirtual
            
            # Convert to more readable format
            for key in ['total_physical', 'available_physical', 
                      'total_pagefile', 'available_pagefile',
                      'total_virtual', 'available_virtual']:
                if key in memory_info:
                    memory_info[f"{key}_formatted"] = self._format_bytes(memory_info[key])
                    
        except Exception as e:
            memory_info['error'] = str(e)
            
        return memory_info
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human-readable string."""
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        value = float(bytes_value)
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
            
        return f"{value:.2f} {units[unit_index]}"


class LinuxPlatform(PlatformInterface):
    """Linux-specific platform implementation."""
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load and return the Linux C library."""
        try:
            return ctypes.CDLL("libc.so.6")
        except Exception as e:
            print(f"Error loading Linux C library: {e}")
            return None
    
    def _add_platform_specific_info(self, info: Dict[str, Any]) -> None:
        """Add Linux-specific information to the info dictionary."""
        # Add Linux distribution information
        try:
            # Try to get distribution info from os-release
            if os.path.exists('/etc/os-release'):
                dist_info = {}
                with open('/etc/os-release', 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            # Remove quotes if present
                            value = value.strip('"\'')
                            dist_info[key] = value
                            
                info['linux_distribution'] = {
                    'name': dist_info.get('NAME', 'Unknown'),
                    'id': dist_info.get('ID', 'unknown'),
                    'version_id': dist_info.get('VERSION_ID', 'unknown'),
                    'pretty_name': dist_info.get('PRETTY_NAME', 'Unknown Linux Distribution')
                }
            # Fallback to lsb_release command
            else:
                returncode, stdout, stderr = self.execute_command(['lsb_release', '-a'])
                if returncode == 0:
                    dist_info = {}
                    for line in stdout.splitlines():
                        if ':' in line:
                            key, value = line.split(':', 1)
                            dist_info[key.strip()] = value.strip()
                            
                    info['linux_distribution'] = {
                        'name': dist_info.get('Distributor ID', 'Unknown'),
                        'version': dist_info.get('Release', 'unknown'),
                        'description': dist_info.get('Description', 'Unknown Linux Distribution')
                    }
        except Exception as e:
            info['linux_distribution_error'] = str(e)
            
        # Add kernel information
        try:
            # Get kernel version
            with open('/proc/version', 'r') as f:
                info['kernel_version'] = f.read().strip()
                
            # Get kernel parameters
            try:
                with open('/proc/cmdline', 'r') as f:
                    info['kernel_cmdline'] = f.read().strip()
            except Exception:
                pass
        except Exception as e:
            info['kernel_info_error'] = str(e)
            
        # Get SELinux status
        try:
            returncode, stdout, stderr = self.execute_command(['sestatus'])
            if returncode == 0:
                for line in stdout.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        if key.strip() == 'SELinux status':
                            info['selinux_status'] = value.strip()
                            break
        except Exception:
            info['selinux_status'] = 'unknown'
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get Linux memory information from /proc/meminfo."""
        memory_info = {}
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if 'kB' in value:
                            # Convert to bytes
                            value = int(value.split()[0]) * 1024
                            memory_info[key] = value
                            memory_info[f"{key}_formatted"] = self._format_bytes(value)
            
            # Calculate percentage of used memory
            if 'MemTotal' in memory_info and 'MemAvailable' in memory_info:
                total = memory_info['MemTotal']
                available = memory_info['MemAvailable']
                used = total - available
                memory_info['memory_used_percent'] = (used / total) * 100
                
        except Exception as e:
            memory_info['error'] = str(e)
            
        return memory_info
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human-readable string."""
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        value = float(bytes_value)
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
            
        return f"{value:.2f} {units[unit_index]}"


class MacOSPlatform(PlatformInterface):
    """macOS-specific platform implementation."""
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load and return the macOS C library."""
        try:
            return ctypes.CDLL("libc.dylib")
        except Exception as e:
            print(f"Error loading macOS C library: {e}")
            return None
    
    def _add_platform_specific_info(self, info: Dict[str, Any]) -> None:
        """Add macOS-specific information to the info dictionary."""
        # Get macOS version information
        try:
            returncode, stdout, stderr = self.execute_command(['sw_vers'])
            if returncode == 0:
                for line in stdout.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == 'ProductName':
                            info['macos_product_name'] = value
                        elif key == 'ProductVersion':
                            info['macos_version'] = value
                        elif key == 'BuildVersion':
                            info['macos_build'] = value
        except Exception as e:
            info['macos_version_error'] = str(e)
            
        # Get hardware model
        try:
            returncode, stdout, stderr = self.execute_command(['sysctl', '-n', 'hw.model'])
            if returncode == 0:
                info['hardware_model'] = stdout.strip()
        except Exception:
            pass
            
        # Check if SIP (System Integrity Protection) is enabled
        try:
            returncode, stdout, stderr = self.execute_command(['csrutil', 'status'])
            if returncode == 0:
                if 'enabled' in stdout.lower():
                    info['sip_enabled'] = True
                elif 'disabled' in stdout.lower():
                    info['sip_enabled'] = False
        except Exception:
            pass
            
        # Check for Rosetta 2 on Apple Silicon
        if 'hardware_model' in info and info['hardware_model'].startswith('Mac'):
            try:
                # Check if running under Rosetta 2
                returncode, stdout, stderr = self.execute_command(['sysctl', '-n', 'sysctl.proc_translated'])
                if returncode == 0 and stdout.strip() == '1':
                    info['running_under_rosetta2'] = True
                else:
                    info['running_under_rosetta2'] = False
            except Exception:
                pass
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get macOS memory information."""
        memory_info = {}
        try:
            # Get total physical memory
            returncode, stdout, stderr = self.execute_command(['sysctl', '-n', 'hw.memsize'])
            if returncode == 0:
                total_memory = int(stdout.strip())
                memory_info['total_physical'] = total_memory
                memory_info['total_physical_formatted'] = self._format_bytes(total_memory)
                
            # Get memory usage with vm_stat command
            returncode, stdout, stderr = self.execute_command(['vm_stat'])
            if returncode == 0:
                # Parse vm_stat output
                page_size = 4096  # Default page size, may vary
                vm_stats = {}
                
                for line in stdout.splitlines():
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        # Extract the number and convert to integer
                        try:
                            value = int(value.strip().rstrip('.').strip())
                            vm_stats[key] = value * page_size  # Convert pages to bytes
                        except ValueError:
                            continue
                
                # Calculate memory usage
                if 'Pages free' in vm_stats and 'total_physical' in memory_info:
                    free_memory = vm_stats['Pages free']
                    memory_info['free_memory'] = free_memory
                    memory_info['free_memory_formatted'] = self._format_bytes(free_memory)
                    
                    used_memory = memory_info['total_physical'] - free_memory
                    memory_info['used_memory'] = used_memory
                    memory_info['used_memory_formatted'] = self._format_bytes(used_memory)
                    
                    # Calculate memory usage percentage
                    memory_info['memory_used_percent'] = (used_memory / memory_info['total_physical']) * 100
                    
        except Exception as e:
            memory_info['error'] = str(e)
            
        return memory_info
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human-readable string."""
        units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        unit_index = 0
        value = float(bytes_value)
        
        while value >= 1024 and unit_index < len(units) - 1:
            value /= 1024
            unit_index += 1
            
        return f"{value:.2f} {units[unit_index]}"


def get_platform_interface() -> PlatformInterface:
    """Factory function to get the appropriate platform interface."""
    if IS_WINDOWS:
        return WindowsPlatform()
    elif IS_LINUX:
        return LinuxPlatform()
    elif IS_MACOS:
        return MacOSPlatform()
    else:
        # Default to a basic implementation
        return PlatformInterface()


def main():
    print(f"{'=' * 50}")
    print(f"Platform Detection and virtualization stats (virtualization is required).")
    print(f"{'=' * 50}")
    
    # Get platform interface
    platform_interface = get_platform_interface()
    
    # Display basic platform information
    print(f"\n[System Information]")
    print(f"Platform: {platform.platform()}")
    print(f"System: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Python: {platform.python_version()} ({platform.python_implementation()})")
    
    # Display processor features
    processor_features = ProcessorFeatures.detect_features()
    print(f"\n[Processor Features]")
    print(f"Detected features: {processor_features}")
    
    feature_list = processor_features.get_feature_names()
    if feature_list:
        print("Feature list:")
        for feature in feature_list:
            print(f"  - {feature}")
    else:
        print("No extended processor features detected")
    
    # Display virtualization information
    print(f"\n[Virtualization Detection]")
    virt_info = platform_interface.detect_virtualization()
    print(f"Virtualized: {virt_info['virtualized']}")
    print(f"Virtualization type: {virt_info['virt_type']}")
    print(f"Confidence: {virt_info['confidence']:.2f}")
    
    if virt_info['evidence']:
        print("Evidence:")
        for evidence in virt_info['evidence']:
            print(f"  - {evidence}")
    
    # Display memory information
    print(f"\n[Memory Information]")
    memory_info = platform_interface.get_memory_info()
    
    # Format display based on platform
    if IS_WINDOWS:
        print(f"Total physical memory: {memory_info.get('total_physical_formatted', 'Unknown')}")
        print(f"Available physical memory: {memory_info.get('available_physical_formatted', 'Unknown')}")
        print(f"Memory load: {memory_info.get('memory_load_percent', 'Unknown')}%")
    elif IS_LINUX:
        print(f"Total memory: {memory_info.get('MemTotal_formatted', 'Unknown')}")
        print(f"Available memory: {memory_info.get('MemAvailable_formatted', 'Unknown')}")
        print(f"Memory used: {memory_info.get('memory_used_percent', 'Unknown'):.1f}%")
    elif IS_MACOS:
        print(f"Total memory: {memory_info.get('total_physical_formatted', 'Unknown')}")
        print(f"Free memory: {memory_info.get('free_memory_formatted', 'Unknown')}")
        print(f"Memory used: {memory_info.get('memory_used_percent', 'Unknown'):.1f}%")
    
    # Display full platform information (condensed for readability)
    print(f"\n[Detailed Platform Information]")
    platform_info = platform_interface.get_platform_info()
    
    # Simplified output of platform details
    if IS_WINDOWS:
        print(f"Windows edition: {platform_info.get('windows_edition', 'Unknown')}")
        print(f"Product name: {platform_info.get('product_name', 'Unknown')}")
        print(f"Current build: {platform_info.get('current_build', 'Unknown')}.{platform_info.get('ubr', 'Unknown')}")
    elif IS_LINUX:
        dist_info = platform_info.get('linux_distribution', {})
        print(f"Distribution: {dist_info.get('pretty_name', 'Unknown Linux Distribution')}")
        print(f"Kernel: {platform_info.get('kernel_version', 'Unknown')}")
    elif IS_MACOS:
        print(f"macOS: {platform_info.get('macos_product_name', 'macOS')} {platform_info.get('macos_version', 'Unknown')}")
        print(f"Build: {platform_info.get('macos_build', 'Unknown')}")
        print(f"Hardware model: {platform_info.get('hardware_model', 'Unknown')}")
        if platform_info.get('running_under_rosetta2') is not None:
            print(f"Running under Rosetta 2: {platform_info['running_under_rosetta2']}")
    
    print(f"\nPlatform detection completed successfully.")


if __name__ == "__main__":
    main()