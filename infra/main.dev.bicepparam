using 'main.bicep'

param namePrefix = 'hfdev'
param location = 'eastus2'
param alertEmail = 'ops@harbor.example'
param tenantId = '00000000-0000-0000-0000-000000000000'
param budgetAmount = 50
param sqlAdminGroupName = 'hf-sql-admins'
param sqlAdminGroupObjectId = '00000000-0000-0000-0000-000000000000'
param deployFoundry = false
param deploySearch = false
param deployApim = false
param deploySql = false
