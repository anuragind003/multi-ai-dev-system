import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from nfs_service import NFSManager
from exceptions import NFSConnectionError, NFSFileNotFoundError, FileOperationError, BulkDownloadError
from config import Settings

# Use a temporary directory for testing NFS interactions
@pytest.fixture(scope="module")
def temp_nfs_mount_path(tmp_path_factory):
    """Creates a temporary directory to simulate an NFS mount point."""
    temp_dir = tmp_path_factory.mktemp("nfs_test_mount")
    # Create some dummy files and directories
    (temp_dir / "dir1").mkdir()
    (temp_dir / "dir1" / "file1.txt").write_text("content of file1")
    (temp_dir / "dir1" / "file2.log").write_text("content of file2")
    (temp_dir / "dir2").mkdir()
    (temp_dir / "dir2" / "sub_dir").mkdir()
    (temp_dir / "dir2" / "sub_dir" / "video.mp4").write_bytes(b"\x00" * 1024 * 1024) # 1MB dummy video
    (temp_dir / "root_file.pdf").write_text("root file content")
    
    yield temp_dir
    # Clean up after tests
    shutil.rmtree(temp_dir)

@pytest.fixture
def nfs_manager(temp_nfs_mount_path):
    """Provides an NFSManager instance configured with the temporary mount path."""
    # Temporarily override settings for the test
    original_nfs_path = Settings.model_fields['NFS_MOUNT_PATH'].default
    Settings.model_fields['NFS_MOUNT_PATH'].default = str(temp_nfs_mount_path)
    
    manager = NFSManager(str(temp_nfs_mount_path))
    yield manager
    
    # Restore original settings
    Settings.model_fields['NFS_MOUNT_PATH'].default = original_nfs_path

def test_nfs_manager_init_success(temp_nfs_mount_path):
    """Test successful initialization of NFSManager."""
    manager = NFSManager(str(temp_nfs_mount_path))
    assert manager.nfs_mount_path == temp_nfs_mount_path

def test_nfs_manager_init_non_existent_path():
    """Test initialization with a non-existent NFS mount path."""
    with pytest.raises(NFSConnectionError, match="NFS mount path 'non_existent_path' not found or accessible."):
        NFSManager("non_existent_path")

def test_nfs_manager_init_inaccessible_path(temp_nfs_mount_path):
    """Test initialization with an inaccessible NFS mount path."""
    with patch('os.scandir', side_effect=OSError("Permission denied")):
        with pytest.raises(NFSConnectionError, match="NFS mount path .* is inaccessible: Permission denied"):
            NFSManager(str(temp_nfs_mount_path))

def test_get_full_file_path_success(nfs_manager, temp_nfs_mount_path):
    """Test getting a full file path."""
    relative_path = "dir1/file1.txt"
    full_path = nfs_manager.get_full_file_path(relative_path)
    assert full_path == temp_nfs_mount_path / relative_path
    assert full_path.is_file()

def test_get_full_file_path_not_found(nfs_manager):
    """Test getting a full file path for a non-existent file."""
    with pytest.raises(NFSFileNotFoundError, match="File not found on NFS: non_existent_file.txt"):
        nfs_manager.get_full_file_path("non_existent_file.txt")

def test_get_full_file_path_traversal_attempt(nfs_manager, temp_nfs_mount_path):
    """Test path traversal prevention."""
    # This path would resolve outside the mount if not handled
    relative_path = "../../../etc/passwd" 
    with pytest.raises(NFSFileNotFoundError, match="Invalid file path"):
        nfs_manager.get_full_file_path(relative_path)

def test_check_file_exists_true(nfs_manager):
    """Test checking existence of an existing file."""
    assert nfs_manager.check_file_exists("dir1/file1.txt") is True

def test_check_file_exists_false(nfs_manager):
    """Test checking existence of a non-existent file."""
    assert nfs_manager.check_file_exists("dir1/non_existent.txt") is False

def test_get_file_size_success(nfs_manager):
    """Test getting file size."""
    size = nfs_manager.get_file_size("dir1/file1.txt")
    assert size == len("content of file1")

def test_get_file_size_not_found(nfs_manager):
    """Test getting file size for a non-existent file."""
    with pytest.raises(NFSFileNotFoundError):
        nfs_manager.get_file_size("non_existent.txt")

def test_get_file_stream_success(nfs_manager):
    """Test streaming a file successfully."""
    stream = nfs_manager.get_file_stream("dir1/file1.txt")
    content = b"".join(stream)
    assert content == b"content of file1"

def test_get_file_stream_not_found(nfs_manager):
    """Test streaming a non-existent file."""
    with pytest.raises(NFSFileNotFoundError):
        list(nfs_manager.get_file_stream("non_existent.txt"))

def test_get_file_stream_read_error(nfs_manager):
    """Test streaming with an underlying read error."""
    with patch('builtins.open', side_effect=OSError("Disk full")):
        with pytest.raises(FileOperationError, match="Failed to read file from NFS: Disk full"):
            list(nfs_manager.get_file_stream("dir1/file1.txt"))

def test_list_files_in_directory_success(nfs_manager):
    """Test listing files in a directory."""
    files = nfs_manager.list_files_in_directory("dir1")
    assert sorted(files) == sorted(["dir1/file1.txt", "dir1/file2.log"])

def test_list_files_in_root_directory(nfs_manager):
    """Test listing files in the root of the mount."""
    files = nfs_manager.list_files_in_directory("")
    assert "root_file.pdf" in files
    assert "dir1" not in files # Should only list files, not directories

def test_list_files_in_non_existent_directory(nfs_manager):
    """Test listing files in a non-existent directory."""
    with pytest.raises(NFSFileNotFoundError, match="Directory not found on NFS: non_existent_dir"):
        nfs_manager.list_files_in_directory("non_existent_dir")

def test_create_temp_zip_file_success(nfs_manager, tmp_path):
    """Test creating a zip file with existing files."""
    output_zip_path = tmp_path / "test_archive.zip"
    file_paths = ["dir1/file1.txt", "dir2/sub_dir/video.mp4"]
    
    created_zip = nfs_manager.create_temp_zip_file(file_paths, output_zip_path)
    
    assert created_zip == output_zip_path
    assert created_zip.is_file()
    
    import zipfile
    with zipfile.ZipFile(created_zip, 'r') as zipf:
        assert sorted(zipf.namelist()) == sorted(["file1.txt", "video.mp4"])
        assert zipf.read("file1.txt") == b"content of file1"
        assert zipf.read("video.mp4") == b"\x00" * 1024 * 1024

def test_create_temp_zip_file_with_missing_file(nfs_manager, tmp_path):
    """Test creating a zip file when one of the requested files is missing."""
    output_zip_path = tmp_path / "test_archive_partial.zip"
    file_paths = ["dir1/file1.txt", "non_existent_file.txt"]
    
    created_zip = nfs_manager.create_temp_zip_file(file_paths, output_zip_path)
    
    assert created_zip.is_file()
    with zipfile.ZipFile(created_zip, 'r') as zipf:
        assert zipf.namelist() == ["file1.txt"] # Only the existing file should be in the zip

def test_create_temp_zip_file_no_valid_files(nfs_manager, tmp_path):
    """Test creating a zip file when no valid files are provided."""
    output_zip_path = tmp_path / "empty_archive.zip"
    file_paths = ["non_existent_file1.txt", "non_existent_file2.txt"]
    
    # The service should handle this gracefully, possibly creating an empty zip
    # or raising an error if no files were added.
    # Current implementation will create an empty zip if no files are valid.
    created_zip = nfs_manager.create_temp_zip_file(file_paths, output_zip_path)
    assert created_zip.is_file()
    with zipfile.ZipFile(created_zip, 'r') as zipf:
        assert zipf.namelist() == []

def test_create_temp_zip_file_write_error(nfs_manager, tmp_path):
    """Test creating a zip file with an underlying write error."""
    output_zip_path = tmp_path / "error_archive.zip"
    file_paths = ["dir1/file1.txt"]
    
    with patch('zipfile.ZipFile', side_effect=OSError("No space left on device")):
        with pytest.raises(BulkDownloadError, match="An unexpected error occurred during zip file creation"):
            nfs_manager.create_temp_zip_file(file_paths, output_zip_path)