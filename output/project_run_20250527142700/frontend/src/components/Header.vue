<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
    <div class="container-fluid">
      <router-link class="navbar-brand" to="/">LTFS Offer CDP</router-link>
      <button
        class="navbar-toggler"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target="#navbarNav"
        aria-controls="navbarNav"
        aria-expanded="false"
        aria-label="Toggle navigation"
      >
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav ms-auto">
          <li class="nav-item">
            <router-link class="nav-link" to="/moengage-export">Moengage Export</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" to="/duplicate-data">Duplicate Data</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" to="/unique-data">Unique Data</router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" to="/error-data">Error Data</router-link>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
export default {
  name: 'Header',
};
</script>

<style scoped>
/* Custom styles for the header can be added here */
.navbar-brand {
  font-weight: bold;
  font-size: 1.5rem;
}

.nav-link {
  font-weight: 500;
  margin-right: 15px; /* Add some spacing between nav items */
}

.nav-link.router-link-exact-active {
  color: #ffffff !important; /* Active link color */
  border-bottom: 2px solid #007bff; /* Highlight active link */
  padding-bottom: 3px;
}
</style>