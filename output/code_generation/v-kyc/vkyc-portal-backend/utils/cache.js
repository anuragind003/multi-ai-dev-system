const NodeCache = require('node-cache');

// Create cache instances for different purposes
const searchCache = new NodeCache({ 
  stdTTL: 300, // 5 minutes
  checkperiod: 60 // Check for expired keys every minute
});

const userCache = new NodeCache({ 
  stdTTL: 1800, // 30 minutes
  checkperiod: 300 
});

const fileCache = new NodeCache({ 
  stdTTL: 600, // 10 minutes
  checkperiod: 120 
});

// Cache middleware for search results
const cacheSearchResults = (duration = 300) => {
  return (req, res, next) => {
    const key = `search:${JSON.stringify(req.query)}`;
    const cachedResult = searchCache.get(key);
    
    if (cachedResult) {
      return res.json(cachedResult);
    }
    
    // Store original send function
    const originalSend = res.json;
    
    // Override send function to cache the response
    res.json = function(data) {
      searchCache.set(key, data, duration);
      originalSend.call(this, data);
    };
    
    next();
  };
};

// Cache middleware for user data
const cacheUserData = (userId) => {
  return (req, res, next) => {
    const key = `user:${userId}`;
    const cachedUser = userCache.get(key);
    
    if (cachedUser) {
      req.user = cachedUser;
      return next();
    }
    
    next();
  };
};

// Cache file metadata
const cacheFileMetadata = (lanId, metadata) => {
  const key = `file:${lanId}`;
  fileCache.set(key, metadata, 600); // 10 minutes
};

const getCachedFileMetadata = (lanId) => {
  const key = `file:${lanId}`;
  return fileCache.get(key);
};

// Clear cache by pattern
const clearCacheByPattern = (pattern) => {
  const keys = searchCache.keys();
  const matchingKeys = keys.filter(key => key.includes(pattern));
  matchingKeys.forEach(key => searchCache.del(key));
};

// Cache statistics
const getCacheStats = () => {
  return {
    search: searchCache.getStats(),
    user: userCache.getStats(),
    file: fileCache.getStats()
  };
};

// Warm up cache with frequently accessed data
const warmupCache = async (db) => {
  try {
    // Cache recent recordings
    const recentRecordings = await db.runQuery(
      'SELECT * FROM recordings ORDER BY date DESC, time DESC LIMIT 20'
    );
    searchCache.set('recent_recordings', recentRecordings, 300);
    
    // Cache user list
    const users = await db.runQuery('SELECT id, username, name, role FROM users');
    users.forEach(user => {
      userCache.set(`user:${user.id}`, user, 1800);
    });
    
    console.log('Cache warmup completed');
  } catch (error) {
    console.error('Cache warmup failed:', error);
  }
};

module.exports = {
  searchCache,
  userCache,
  fileCache,
  cacheSearchResults,
  cacheUserData,
  cacheFileMetadata,
  getCachedFileMetadata,
  clearCacheByPattern,
  getCacheStats,
  warmupCache
}; 