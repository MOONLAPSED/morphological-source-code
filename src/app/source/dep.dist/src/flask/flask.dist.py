import ctypes
import platform
import sys
import os
import re
from enum import IntFlag, auto
from typing import Optional, Dict, Any, List, Tuple, Callable

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


class WindowsPlatform(PlatformInterface):
    """Windows-specific platform implementation."""
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load the Windows C runtime library."""
        try:
            # Try to load msvcrt.dll (C runtime)
            libc = ctypes.CDLL("msvcrt.dll")
            return libc
        except OSError as e:
            print(f"Error loading C library on Windows: {e}")
            
            # Try alternative libraries if msvcrt fails
            try:
                # Try loading kernel32.dll
                kernel32 = ctypes.WinDLL("kernel32.dll")
                return kernel32
            except OSError as e2:
                print(f"Error loading kernel32.dll: {e2}")
                return None
    
    def _add_platform_specific_info(self, info: Dict[str, Any]) -> None:
        """Add Windows-specific information to the info dictionary."""
        try:
            # Windows version information
            info['windows_version'] = sys.getwindowsversion()
            
            # Get Windows edition information
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            info['windows_product_name'] = winreg.QueryValueEx(key, "ProductName")[0]
            info['windows_edition_id'] = winreg.QueryValueEx(key, "EditionID")[0]
            
            # CPU information
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                               r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            info['cpu_name'] = winreg.QueryValueEx(key, "ProcessorNameString")[0]
            info['cpu_vendor'] = winreg.QueryValueEx(key, "VendorIdentifier")[0]
            info['cpu_mhz'] = winreg.QueryValueEx(key, "~MHz")[0]
            
        except Exception as e:
            info['windows_details_error'] = str(e)
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get Windows system memory information."""
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
            
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
            if not kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status)):
                error = ctypes.get_last_error()
                raise ctypes.WinError(error)
                
            return {
                'total_physical': memory_status.ullTotalPhys,
                'available_physical': memory_status.ullAvailPhys,
                'total_virtual': memory_status.ullTotalVirtual,
                'available_virtual': memory_status.ullAvailVirtual,
                'memory_load_percent': memory_status.dwMemoryLoad,
                'total_pagefile': memory_status.ullTotalPageFile,
                'available_pagefile': memory_status.ullAvailPageFile,
            }
            
        except Exception as e:
            print(f"Error getting Windows memory info: {e}")
            return {'error': str(e)}
    
class LinuxPlatform(PlatformInterface):
    """Linux-specific platform implementation."""
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load the Linux C library."""
        try:
            # Try to load standard C library
            libc = ctypes.CDLL("libc.so.6")
            return libc
        except OSError as e:
            print(f"Error loading libc.so.6: {e}")
            
            # Try alternative libraries if libc.so.6 fails
            try:
                # Some systems use different paths
                libc = ctypes.CDLL("libc.so")
                return libc
            except OSError as e2:
                print(f"Error loading libc.so: {e2}")
                
                # Last resort - try to find libc dynamically
                try:
                    import ctypes.util
                    libc_path = ctypes.util.find_library('c')
                    if libc_path:
                        libc = ctypes.CDLL(libc_path)
                        return libc
                except OSError as e3:
                    print(f"Error loading dynamically found libc: {e3}")
                    
                return None
    
    def _add_platform_specific_info(self, info: Dict[str, Any]) -> None:
        """Add Linux-specific information to the info dictionary."""
        try:
            # Get Linux distribution info
            if hasattr(platform, 'freedesktop_os_release'):
                # Python 3.10+ has built-in support
                os_release = platform.freedesktop_os_release()
                info['linux_distro'] = os_release.get('NAME', 'Unknown')
                info['linux_version'] = os_release.get('VERSION', 'Unknown')
                info['linux_id'] = os_release.get('ID', 'Unknown')
            else:
                # Fallback for older Python versions
                try:
                    with open('/etc/os-release', 'r') as f:
                        lines = f.readlines()
                        os_release = {}
                        for line in lines:
                            if '=' in line:
                                key, value = line.strip().split('=', 1)
                                os_release[key] = value.strip('"\'')
                        info['linux_distro'] = os_release.get('NAME', 'Unknown')
                        info['linux_version'] = os_release.get('VERSION', 'Unknown')
                        info['linux_id'] = os_release.get('ID', 'Unknown')
                except Exception:
                    info['linux_distro'] = 'Unknown'
                    info['linux_version'] = 'Unknown'
            
            # Get kernel information
            returncode, stdout, stderr = self.execute_command(['uname', '-r'])
            if returncode == 0:
                info['kernel_version'] = stdout.strip()
                
            # Get CPU information
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = f.read()
                    
                # Extract CPU model name
                model_match = re.search(r'model name\s+:\s+(.*)', cpuinfo)
                if model_match:
                    info['cpu_model'] = model_match.group(1)
                    
                # Count CPU cores
                info['cpu_cores'] = cpuinfo.count('processor\t:')
            except Exception as e:
                info['cpu_info_error'] = str(e)
                
        except Exception as e:
            info['linux_details_error'] = str(e)
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get Linux system memory information."""
        try:
            # Parse /proc/meminfo for memory information
            memory_info = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        if value.endswith(' kB'):
                            # Convert kB to bytes
                            value = int(value[:-3]) * 1024
                        memory_info[key] = value
            
            result = {
                'total_physical': int(memory_info.get('MemTotal', 0)),
                'available_physical': int(memory_info.get('MemAvailable', 0)),
                'free_physical': int(memory_info.get('MemFree', 0)),
                'buffers': int(memory_info.get('Buffers', 0)),
                'cached': int(memory_info.get('Cached', 0)),
                'swap_total': int(memory_info.get('SwapTotal', 0)),
                'swap_free': int(memory_info.get('SwapFree', 0)),
            }
            
            # Calculate used memory
            result['used_physical'] = result['total_physical'] - result['free_physical'] - result['buffers'] - result['cached']
            
            return result
            
        except Exception as e:
            print(f"Error getting Linux memory info: {e}")
            return {'error': str(e)}


class MacOSPlatform(PlatformInterface):
    """macOS-specific platform implementation."""
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Load the macOS C library."""
        try:
            # Try to load C library on macOS
            libc = ctypes.CDLL("libc.dylib")
            return libc
        except OSError as e:
            print(f"Error loading libc.dylib: {e}")
            
            # Try alternative libraries if libc.dylib fails
            try:
                # Use ctypes.util to find the C library
                import ctypes.util
                libc_path = ctypes.util.find_library('c')
                if libc_path:
                    libc = ctypes.CDLL(libc_path)
                    return libc
            except OSError as e2:
                print(f"Error loading dynamically found libc: {e2}")
                
            return None
    
    def _add_platform_specific_info(self, info: Dict[str, Any]) -> None:
        """Add macOS-specific information to the info dictionary."""
        try:
            # Get macOS version details
            import subprocess
            
            # Get macOS version
            result = subprocess.run(['sw_vers', '-productVersion'], 
                                   capture_output=True, text=True, check=False)
            if result.returncode == 0:
                info['macos_version'] = result.stdout.strip()
            
            # Get macOS build number
            result = subprocess.run(['sw_vers', '-buildVersion'], 
                                   capture_output=True, text=True, check=False)
            if result.returncode == 0:
                info['macos_build'] = result.stdout.strip()
                
            # Get CPU information
            result = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'], 
                                   capture_output=True, text=True, check=False)
            if result.returncode == 0:
                info['cpu_model'] = result.stdout.strip()
                
            # Get CPU core count
            result = subprocess.run(['sysctl', '-n', 'hw.physicalcpu'], 
                                   capture_output=True, text=True, check=False)
            if result.returncode == 0:
                info['physical_cpu_cores'] = int(result.stdout.strip())
                
            result = subprocess.run(['sysctl', '-n', 'hw.logicalcpu'], 
                                   capture_output=True, text=True, check=False)
            if result.returncode == 0:
                info['logical_cpu_cores'] = int(result.stdout.strip())
                
        except Exception as e:
            info['macos_details_error'] = str(e)
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get macOS system memory information."""
        try:
            import subprocess
            
            # Get total physical memory
            result = subprocess.run(['sysctl', '-n', 'hw.memsize'], 
                                   capture_output=True, text=True, check=False)
            total_memory = int(result.stdout.strip()) if result.returncode == 0 else 0
            
            # Get vm_stat for memory statistics
            result = subprocess.run(['vm_stat'], 
                                   capture_output=True, text=True, check=False)
            
            # Parse vm_stat output
            memory_stats = {}
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        # Convert value (usually has form "  XXXXX.")
                        try:
                            value = int(value.strip().rstrip('.')) * 4096  # 4KB page size
                            memory_stats[key.strip()] = value
                        except ValueError:
                            pass
            
            # Calculate memory metrics
            free_memory = memory_stats.get('Pages free', 0)
            active_memory = memory_stats.get('Pages active', 0)
            inactive_memory = memory_stats.get('Pages inactive', 0)
            wired_memory = memory_stats.get('Pages wired down', 0)
            compressed_memory = memory_stats.get('Pages occupied by compressor', 0)
            
            # Available memory is free + inactive (can be reclaimed)
            available_memory = free_memory + inactive_memory
            
            # Used memory is total - available
            used_memory = total_memory - available_memory
            
            return {
                'total_physical': total_memory,
                'available_physical': available_memory,
                'used_physical': used_memory,
                'free': free_memory,
                'active': active_memory,
                'inactive': inactive_memory,
                'wired': wired_memory,
                'compressed': compressed_memory
            }
            
        except Exception as e:
            print(f"Error getting macOS memory info: {e}")
            return {'error': str(e)}

class PlatformFactory:
    """Factory class for creating the appropriate platform interface."""
    
    @staticmethod
    def create_platform() -> PlatformInterface:
        """Create and return the appropriate platform interface based on the current system."""
        try:
            if IS_WINDOWS:
                return WindowsPlatform()
            elif IS_LINUX:
                return LinuxPlatform()
            elif IS_MACOS:
                return MacOSPlatform()
            else:
                print(f"Warning: Unsupported platform {sys.platform}, using generic platform interface")
                return PlatformInterface()  # Fallback to generic implementation
        except Exception as e:
            print(f"Error creating platform interface: {e}")
            # Last resort fallback
            return PlatformInterface()
    
    @staticmethod
    def create_specific_platform(platform_type: str) -> Optional[PlatformInterface]:
        """Create a specific platform interface regardless of the current system."""
        try:
            if platform_type.lower() == 'windows':
                return WindowsPlatform()
            elif platform_type.lower() == 'linux':
                return LinuxPlatform()
            elif platform_type.lower() in ('macos', 'darwin', 'mac'):
                return MacOSPlatform()
            else:
                print(f"Unknown platform type: {platform_type}")
                return None
        except Exception as e:
            print(f"Error creating specific platform interface: {e}")
            return None


class FallbackPlatformInterface(PlatformInterface):
    """Resilient fallback platform interface that tries multiple approaches."""
    
    def __init__(self):
        """Initialize with multiple platform interfaces as fallbacks."""
        super().__init__()
        self._platforms = []
        self._current_platform = None
        
        # Try to create all platform interfaces
        for platform_class in [WindowsPlatform, LinuxPlatform, MacOSPlatform]:
            try:
                self._platforms.append(platform_class())
            except Exception:
                pass
        
        # Set the most appropriate platform as current
        self._select_appropriate_platform()
    
    def _select_appropriate_platform(self) -> None:
        """Select the most appropriate platform based on the current system."""
        # First try the native platform
        if IS_WINDOWS:
            for platform in self._platforms:
                if isinstance(platform, WindowsPlatform):
                    self._current_platform = platform
                    return
        elif IS_LINUX:
            for platform in self._platforms:
                if isinstance(platform, LinuxPlatform):
                    self._current_platform = platform
                    return
        elif IS_MACOS:
            for platform in self._platforms:
                if isinstance(platform, MacOSPlatform):
                    self._current_platform = platform
                    return
        
        # If no matching platform, use the first available
        if self._platforms:
            self._current_platform = self._platforms[0]
    
    def _try_all_platforms(self, method_name: str, *args, **kwargs) -> Any:
        """Try a method on all available platforms until one succeeds."""
        # First try the current selected platform
        if self._current_platform:
            try:
                method = getattr(self._current_platform, method_name)
                return method(*args, **kwargs)
            except Exception as e:
                print(f"Error with current platform {type(self._current_platform).__name__}.{method_name}: {e}")
        
        # Try all other platforms
        for platform in self._platforms:
            if platform is not self._current_platform:
                try:
                    method = getattr(platform, method_name)
                    return method(*args, **kwargs)
                except Exception as e:
                    print(f"Error with fallback platform {type(platform).__name__}.{method_name}: {e}")
        
        # If all platforms fail, raise exception
        raise RuntimeError(f"All platforms failed for method {method_name}")
    
    def load_c_library(self) -> Optional[ctypes.CDLL]:
        """Try to load a C library using all available platforms."""
        try:
            return self._try_all_platforms('load_c_library')
        except Exception as e:
            print(f"All platforms failed to load C library: {e}")
            return None
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory info using all available platforms."""
        try:
            return self._try_all_platforms('get_memory_info')
        except Exception as e:
            print(f"All platforms failed to get memory info: {e}")
            return {'error': str(e)}

# Enhanced platform factory with resilient fallback option
class EnhancedPlatformFactory:
    """Enhanced factory class with resilient fallback options."""
    
    @staticmethod
    def create_platform(resilient: bool = True) -> PlatformInterface:
        """
        Create and return the appropriate platform interface.
        
        Args:
            resilient: If True, returns a resilient platform interface that tries
                      multiple approaches if the primary one fails.
        """
        try:
            if resilient:
                return FallbackPlatformInterface()
            else:
                return PlatformFactory.create_platform()
        except Exception as e:
            print(f"Error creating platform: {e}")
            # Ultimate fallback
            return PlatformInterface()


# Module level convenience function
def get_platform(resilient: bool = True) -> PlatformInterface:
    """
    Get the appropriate platform interface for the current system.
    
    Args:
        resilient: If True, returns a resilient platform interface that tries
                  multiple approaches if the primary one fails.
    
    Returns:
        A platform interface instance appropriate for the current system.
    """
    return EnhancedPlatformFactory.create_platform(resilient)


# Add a function to detect virtualization environment
def detect_virtualization() -> Dict[str, Any]:
    """Detect if running in a virtualized environment."""
    result = {'virtualized': False, 'type': None, 'evidence': []}
    
    # Common detection methods
    if IS_LINUX:
        try:
            # Check dmesg for virtualization hints
            returncode, stdout, stderr = PlatformInterface().execute_command(['dmesg'])
            if returncode == 0:
                stdout_lower = stdout.lower()
                
                # Check for various virtualization technologies
                if 'vmware' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'VMware'
                    result['evidence'].append('dmesg contains VMware references')
                elif 'virtualbox' in stdout_lower or 'vbox' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'VirtualBox'
                    result['evidence'].append('dmesg contains VirtualBox references')
                elif 'kvm' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'KVM'
                    result['evidence'].append('dmesg contains KVM references')
                elif 'xen' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'Xen'
                    result['evidence'].append('dmesg contains Xen references')
                elif 'hyper-v' in stdout_lower or 'hyperv' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'Hyper-V'
                    result['evidence'].append('dmesg contains Hyper-V references')
                elif 'docker' in stdout_lower or 'container' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'Container'
                    result['evidence'].append('dmesg contains container references')
            
            # Check for specific virtual files
            virtual_files = [
                ('/sys/hypervisor/type', 'hypervisor type file exists'),
                ('/proc/xen', 'Xen proc file exists'),
                ('/proc/self/cgroup', 'cgroups might indicate container')
            ]
            
            for vfile, evidence in virtual_files:
                if os.path.exists(vfile):
                    try:
                        with open(vfile, 'r') as f:
                            content = f.read().lower()
                            result['evidence'].append(f"{evidence}: {content[:50]}...")
                            
                            # Set virtualization type based on content
                            if 'xen' in content:
                                result['virtualized'] = True
                                result['type'] = 'Xen'
                            elif 'kvm' in content:
                                result['virtualized'] = True
                                result['type'] = 'KVM'
                            elif 'vmware' in content:
                                result['virtualized'] = True
                                result['type'] = 'VMware'
                            elif 'docker' in content or 'lxc' in content:
                                result['virtualized'] = True
                                result['type'] = 'Container'
                    except Exception:
                        pass
                        
            # Check using systemd-detect-virt if available
            returncode, stdout, stderr = PlatformInterface().execute_command(['systemd-detect-virt'])
            if returncode == 0 and stdout.strip() not in ('none', ''):
                result['virtualized'] = True
                result['type'] = stdout.strip()
                result['evidence'].append(f"systemd-detect-virt reports: {stdout.strip()}")
                
        except Exception as e:
            result['error'] = str(e)
            
    elif IS_WINDOWS:
        try:
            import winreg
            
            # Check for common registry keys that indicate virtualization
            virt_indicators = [
                (r'SYSTEM\CurrentControlSet\Control\VirtualDeviceDrivers', 'Registry contains virtual device drivers'),
                (r'SYSTEM\CurrentControlSet\Services\VMTools', 'VMware Tools service exists'),
                (r'SYSTEM\CurrentControlSet\Services\VBoxService', 'VirtualBox service exists'),
                (r'SOFTWARE\VMware, Inc.', 'VMware software registry key exists'),
                (r'SOFTWARE\Oracle\VirtualBox Guest Additions', 'VirtualBox Additions registry key exists')
            ]
            
            for reg_path, evidence in virt_indicators:
                try:
                    hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
                    winreg.CloseKey(hkey)
                    result['virtualized'] = True
                    result['evidence'].append(evidence)
                    
                    if 'vmware' in reg_path.lower():
                        result['type'] = 'VMware'
                    elif 'virtualbox' in reg_path.lower() or 'vbox' in reg_path.lower():
                        result['type'] = 'VirtualBox'
                except FileNotFoundError:
                    pass
                    
            # Check for specific Windows virtual devices
            try:
                # Look for VMware virtual hardware
                hkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                                     r'HARDWARE\DESCRIPTION\System\BIOS')
                smbios = winreg.QueryValueEx(hkey, 'SystemManufacturer')[0]
                if 'vmware' in smbios.lower():
                    result['virtualized'] = True
                    result['type'] = 'VMware'
                    result['evidence'].append(f"BIOS reports VMware: {smbios}")
                elif 'innotek' in smbios.lower() or 'virtualbox' in smbios.lower():
                    result['virtualized'] = True
                    result['type'] = 'VirtualBox'
                    result['evidence'].append(f"BIOS reports VirtualBox: {smbios}")
                elif 'microsoft corporation' in smbios.lower() and 'virtual' in smbios.lower():
                    result['virtualized'] = True
                    result['type'] = 'Hyper-V'
                    result['evidence'].append(f"BIOS reports Microsoft Hyper-V: {smbios}")
                winreg.CloseKey(hkey)
            except Exception:
                pass
                
        except Exception as e:
            result['error'] = str(e)
            
    elif IS_MACOS:
        try:
            # Check for common virtualization indicators on macOS
            returncode, stdout, stderr = PlatformInterface().execute_command(['system_profiler', 'SPHardwareDataType'])
            
            if returncode == 0:
                stdout_lower = stdout.lower()
                
                # Check for virtualization clues in hardware info
                if 'parallels' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'Parallels'
                    result['evidence'].append('system_profiler contains Parallels references')
                elif 'vmware' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'VMware'
                    result['evidence'].append('system_profiler contains VMware references')
                elif 'virtualbox' in stdout_lower:
                    result['virtualized'] = True
                    result['type'] = 'VirtualBox'
                    result['evidence'].append('system_profiler contains VirtualBox references')
                
                # Look for specific model identifiers
                model_match = re.search(r'model (?:name|identifier):\s*(.+)', stdout_lower)
                if model_match:
                    model = model_match.group(1)
                    if 'virtual' in model:
                        result['virtualized'] = True
                        result['evidence'].append(f"Virtual machine model: {model}")
                        
        except Exception as e:
            result['error'] = str(e)
    
    return result

def require_virtualization(self, exit_on_failure=True, error_message="This application must run in a virtualized environment for safety."):
    """Enforce that the application runs only in virtualized environments."""
    virt_status = self.detect_virtualization()
    
    if not virt_status['virtualized']:
        if exit_on_failure:
            print(error_message)
            print("Virtualization not detected. Exiting for safety.")
            sys.exit(1)
        else:
            # Maybe limit functionality instead
            return False
    return True

# Add the detect_virtualization method to PlatformInterface
PlatformInterface.detect_virtualization = detect_virtualization

# Example usage of the platform factory
def main():
    """Example usage of the platform detection system."""
    try:
        print("Platform Detection System")
        print("========================")
        
        # Create platform using the factory
        platform_interface = get_platform(resilient=True)
        
        # Get platform information
        platform_info = platform_interface.get_platform_info()
        print("\nPlatform Information:")
        for key, value in platform_info.items():
            print(f"  {key}: {value}")
        
        # Get processor features
        features = platform_interface.processor_features
        print("\nProcessor Features:")
        for feature_name in features.get_feature_names():
            print(f"  {feature_name}")
        
        # Get memory information
        memory_info = platform_interface.get_memory_info()
        print("\nMemory Information:")
        for key, value in memory_info.items():
            if isinstance(value, int) and key.endswith(('_physical', '_virtual', 'total', 'available', 'free')):
                # Convert bytes to MB for readability
                print(f"  {key}: {value / (1024 * 1024):.2f} MB")
            else:
                print(f"  {key}: {value}")
        
        # Check virtualization
        virt_info = detect_virtualization()
        print("\nVirtualization Check:")
        print(f"  Virtualized: {virt_info['virtualized']}")
        if virt_info['virtualized']:
            print(f"  Type: {virt_info['type']}")
            print("  Evidence:")
            for evidence in virt_info['evidence']:
                print(f"    - {evidence}")
        
    except Exception as e:
        print(f"Error in platform detection demo: {e}")

if __name__ == "__main__":
    main()