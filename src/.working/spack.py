import sys
import os
import site

# Get the path to site-packages
site_packages_paths = site.getsitepackages()

# Print site-packages paths for reference
print("Site-packages paths:", site_packages_paths)

# Environment variable index
env_var_index = 1

# Iterate through each site-packages path
for site_packages in site_packages_paths:
    # Walk through the site-packages directory
    for root, dirs, files in os.walk(site_packages):
        for name in dirs + files:
            # Form the full path
            full_path = os.path.join(root, name)
            
            # Set the environment variable
            env_var_name = f"SITE_PACKAGES_CONTENT_{env_var_index}"
            os.environ[env_var_name] = full_path
            
            # Print the environment variable for reference
            print(f"{env_var_name}={full_path}")
            
            # Increment the index for the next environment variable
            env_var_index += 1

