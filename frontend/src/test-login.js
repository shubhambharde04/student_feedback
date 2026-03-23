// Test login API directly
import API from './api.js';

const testLogin = async () => {
  try {
    console.log('Testing login API...');
    
    // Test with the user we created
    const response = await API.post('auth/login/', {
      username: 'testuser',
      password: 'testpass123'
    });
    
    console.log('✅ Login successful:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Login failed:', error.response?.data || error.message);
    throw error;
  }
};

// Run test
testLogin()
  .then(data => {
    console.log('Tokens received:', {
      access: data.access ? '✅' : '❌',
      refresh: data.refresh ? '✅' : '❌',
      user: data.user ? '✅' : '❌'
    });
  })
  .catch(err => console.error('Test failed:', err));
