@allowed([
  'TRANSITIONAL_STATIC_EGRESS'
  'PRIVATE_VNET_TARGET'
])
param networkMode string

param allowedHetznerEgressCidrs array
param privateEndpointSubnetResourceId string
param privateDnsZoneResourceIds array
param privateEndpointConnectionResourceIds array

var isTransitionalStaticEgress = networkMode == 'TRANSITIONAL_STATIC_EGRESS'

// Transitional static egress is Non-Production-only and must be paired with
// exact Hetzner egress CIDRs. The local validator blocks empty and allow-all
// CIDR lists before deployment review.
var transitionalNetworkAcls = {
  defaultAction: 'Deny'
  bypass: 'None'
  ipRules: [
    for cidr in allowedHetznerEgressCidrs: {
      value: cidr
    }
  ]
  virtualNetworkRules: []
}

// Private endpoint IDs are contract parameters for the later production target.
// This module does not claim that Hetzner can reach private endpoints without a
// VPN or Azure-hosted worker.
var privateTargetNetworkAcls = {
  defaultAction: 'Deny'
  bypass: 'None'
  ipRules: []
  virtualNetworkRules: []
}

output publicNetworkAccess string = isTransitionalStaticEgress ? 'Enabled' : 'Disabled'
output networkAcls object = isTransitionalStaticEgress ? transitionalNetworkAcls : privateTargetNetworkAcls
output privateEndpointSubnetContract string = privateEndpointSubnetResourceId
output privateDnsZoneContract array = privateDnsZoneResourceIds
output privateEndpointConnectionContract array = privateEndpointConnectionResourceIds
