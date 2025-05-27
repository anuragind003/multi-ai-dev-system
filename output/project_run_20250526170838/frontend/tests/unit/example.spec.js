import { mount } from '@vue/test-utils';
import FileUploadComponent from '@/components/FileUploadComponent.vue'; // Assuming '@/components' alias points to 'src/components'

// Mock the global fetch API for unit testing network requests
const mockFetch = jest.spyOn(global, 'fetch');

describe('FileUploadComponent.vue', () => {
  let wrapper;

  // Before each test, mount the component and clear mocks
  beforeEach(() => {
    mockFetch.mockClear(); // Clear any previous mock calls
    wrapper = mount(FileUploadComponent);
  });

  // After each test, unmount the component to clean up
  afterEach(() => {
    wrapper.unmount();
  });

  it('renders the upload form elements correctly', () => {
    expect(wrapper.find('h2').text()).toBe('Upload Customer Data');
    expect(wrapper.find('input[type="file"]').exists()).toBe(true);
    expect(wrapper.find('button').text()).toBe('Upload');
    // Initially, the upload button should be disabled as no file is selected
    expect(wrapper.find('button').attributes('disabled')).toBeDefined();
  });

  it('enables the upload button when a file is selected', async () => {
    const fileInput = wrapper.find('input[type="file"]');
    // Create a mock File object
    const mockFile = new File(['dummy content'], 'customer_data.csv', { type: 'text/csv' });

    // Simulate selecting a file by setting the 'files' property on the input element
    // and then triggering the 'change' event.
    Object.defineProperty(fileInput.element, 'files', {
      value: [mockFile],
      writable: true,
    });
    await fileInput.trigger('change');

    // Assert that the component's selectedFile data property is updated
    expect(wrapper.vm.selectedFile).toBe(mockFile);
    // Assert that the upload button is now enabled
    expect(wrapper.find('button').attributes('disabled')).toBeUndefined();
  });

  it('displays a message if upload is attempted without selecting a file', async () => {
    // Click the upload button without selecting a file
    await wrapper.find('button').trigger('click');

    // Assert that the status message is displayed
    expect(wrapper.find('p').text()).toBe('Please select a file first.');
    // Assert that fetch was not called
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('handles successful file upload and emits upload-success event', async () => {
    const fileInput = wrapper.find('input[type="file"]');
    const mockFile = new File(['dummy content'], 'customer_data.csv', { type: 'text/csv' });

    // Simulate file selection
    Object.defineProperty(fileInput.element, 'files', {
      value: [mockFile],
      writable: true,
    });
    await fileInput.trigger('change');

    // Mock a successful API response
    const mockSuccessResponse = {
      status: 'success',
      log_id: 'a1b2c3d4-e5f6-7890-1234-567890abcdef',
      success_count: 100,
      error_count: 5,
    };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockSuccessResponse),
    });

    // Click the upload button
    await wrapper.find('button').trigger('click');

    // Assert that fetch was called with the correct endpoint and method
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledWith('/admin/customer-data/upload', expect.objectContaining({
      method: 'POST',
      body: expect.any(FormData), // Expecting FormData object
    }));

    // Wait for the DOM to update after the async operation completes
    await wrapper.vm.$nextTick();

    // Assert that the success message is displayed
    expect(wrapper.find('p').text()).toBe(`Upload successful! Success: ${mockSuccessResponse.success_count}, Errors: ${mockSuccessResponse.error_count}`);
    // Assert that the 'upload-success' event was emitted with the correct payload
    expect(wrapper.emitted('upload-success')).toBeTruthy();
    expect(wrapper.emitted('upload-success')[0][0]).toEqual(mockSuccessResponse);

    // Assert that the selected file and input field are cleared
    expect(wrapper.vm.selectedFile).toBeNull();
    expect(wrapper.find('input[type="file"]').element.value).toBe('');
  });

  it('handles failed file upload and emits upload-fail event', async () => {
    const fileInput = wrapper.find('input[type="file"]');
    const mockFile = new File(['dummy content'], 'invalid_data.csv', { type: 'text/csv' });

    // Simulate file selection
    Object.defineProperty(fileInput.element, 'files', {
      value: [mockFile],
      writable: true,
    });
    await fileInput.trigger('change');

    // Mock a failed API response (e.g., 400 Bad Request)
    const mockErrorResponse = { message: 'Invalid file format or missing required columns.' };
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: () => Promise.resolve(mockErrorResponse),
    });

    // Click the upload button
    await wrapper.find('button').trigger('click');

    // Wait for the DOM to update
    await wrapper.vm.$nextTick();

    // Assert that the error message is displayed
    expect(wrapper.find('p').text()).toBe(`Upload failed: ${mockErrorResponse.message}`);
    // Assert that the 'upload-fail' event was emitted with the error payload
    expect(wrapper.emitted('upload-fail')).toBeTruthy();
    expect(wrapper.emitted('upload-fail')[0][0]).toEqual(mockErrorResponse);
  });

  it('handles network errors during upload and emits upload-error event', async () => {
    const fileInput = wrapper.find('input[type="file"]');
    const mockFile = new File(['dummy content'], 'network_test.csv', { type: 'text/csv' });

    // Simulate file selection
    Object.defineProperty(fileInput.element, 'files', {
      value: [mockFile],
      writable: true,
    });
    await fileInput.trigger('change');

    // Mock a network error (e.g., no internet connection)
    const networkError = new Error('Failed to fetch');
    mockFetch.mockRejectedValueOnce(networkError);

    // Click the upload button
    await wrapper.find('button').trigger('click');

    // Wait for the DOM to update
    await wrapper.vm.$nextTick();

    // Assert that the network error message is displayed
    expect(wrapper.find('p').text()).toBe(`Upload error: ${networkError.message}`);
    // Assert that the 'upload-error' event was emitted with the error object
    expect(wrapper.emitted('upload-error')).toBeTruthy();
    expect(wrapper.emitted('upload-error')[0][0]).toEqual(networkError);
  });
});