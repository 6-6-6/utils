use ipnet::Ipv6Net;
use std::net::Ipv6Addr;

/// construct an Ipv6Addr from a vector
/// # Safety
///
/// this function interpretes a vector of u8 as u128, so make sure it conatins more than 16 elements!!
///
/// # Example
///
/// ```
/// use address_translation::construct_v6addr_unchecked;
/// use std::net::Ipv6Addr;
///
/// let n = 100;
/// let octets = vec![0; n];
/// let addr = unsafe { construct_v6addr_unchecked(&octets) };
///
/// assert_eq!(Ipv6Addr::UNSPECIFIED, addr);
/// ```
#[inline]
pub unsafe fn construct_v6addr_unchecked(segments: &[u8]) -> Ipv6Addr {
    Ipv6Addr::from((*(segments.as_ptr() as *const u128)).to_be())
}

/// construct an Ipv6Addr from a vector of u8, it will make sure the vector has more than 16 elements
///
/// # Example
///
/// ```
/// use address_translation::construct_v6addr;
/// use std::net::Ipv6Addr;
///
/// let ref_addr: Ipv6Addr = "2001:db8::1".parse().unwrap();
///
/// let addr = construct_v6addr(&[
///     0x20u8, 0x01,
///     0x0d, 0xb8,
///     0, 0,
///     0, 0,
///     0, 0,
///     0, 0,
///     0, 0,
///     0, 0x1]);
/// 
/// let addr2 = construct_v6addr(&[]);
///
/// assert_eq!(Some(ref_addr), addr);
/// assert_eq!(None, addr2);
/// ```
#[inline]
pub fn construct_v6addr(segments: &[u8]) -> Option<Ipv6Addr> {
    if segments.len() < 16 {
        None
    } else {
        unsafe { Some(construct_v6addr_unchecked(segments)) }
    }
}

/// calculate checksum for NPTv6, see [nptv6](crate::nptv6)
pub fn pfx_csum(prefix: &Ipv6Net) -> u16 {
    let mut ret: i32 = 0;
    for x in prefix.network().segments().iter() {
        ret += *x as i32;
    }
    ((ret.rem_euclid(0xffff)) ^ 0xffff) as u16
}

/// perform IPv6-to-IPv6 Network Prefix Translation
///
/// for details, see <https://datatracker.ietf.org/doc/html/rfc6296>
///
/// # Example
///
/// ```
/// use ipnet::Ipv6Net;
/// use std::net::Ipv6Addr;
/// use address_translation::{pfx_csum, nptv6};
///
/// let upstream_pfx: Ipv6Net = "2001:db9::/64".parse().unwrap();
/// let upstream_pfx_csum = pfx_csum(&upstream_pfx);
///
/// let downstream_pfx: Ipv6Net = "2001:db9:beef::/64".parse().unwrap();
/// let downstream_pfx_csum = pfx_csum(&downstream_pfx);
///
/// let incoming_addr: Ipv6Addr = "2001:db9::feed".parse().unwrap();
///
/// let outcoming_addr_predicted: Ipv6Addr = "2001:db9:beef:0:4110::feed".parse().unwrap();
/// let outcoming_addr = nptv6(
///     upstream_pfx_csum,
///     downstream_pfx_csum,
///     incoming_addr,
///     &downstream_pfx);
///
/// let incoming_addr_reverted = nptv6(
///     downstream_pfx_csum,
///     upstream_pfx_csum,
///     outcoming_addr,
///     &upstream_pfx);
///
/// assert_eq!(outcoming_addr, outcoming_addr_predicted);
/// assert_eq!(incoming_addr, incoming_addr_reverted);
/// ```
pub fn nptv6(
    upstream_pfx_csum: u16,
    downstream_pfx_csum: u16,
    upstream_addr: Ipv6Addr,
    downstream_pfx: &Ipv6Net,
) -> Ipv6Addr {
    let pfx_len = downstream_pfx.prefix_len() / 16;
    let mut segments = upstream_addr.segments();
    let downstream_segs = downstream_pfx.network().segments();
    let to_be_translated_segment = segments[pfx_len as usize];

    let sum2 =
        downstream_pfx_csum as i32 - upstream_pfx_csum as i32 + to_be_translated_segment as i32;

    let mut i: usize = 0;
    while i < pfx_len as usize {
        segments[i] = downstream_segs[i];
        i += 1;
    }

    segments[pfx_len as usize] = sum2.rem_euclid(0xffff) as u16;
    Ipv6Addr::from(segments)
}

/// rewrite the prefix of an Ipv6Addr
///
/// for details, see <https://www.netfilter.org/documentation/HOWTO/netfilter-extensions-HOWTO-4.html#ss4.4>
///
/// # Example
///
/// ```
/// use ipnet::Ipv6Net;
/// use std::net::Ipv6Addr;
/// use address_translation::{netmapv6};
///
/// let upstream_pfx: Ipv6Net = "2001:db9::/64".parse().unwrap();
/// let downstream_pfx: Ipv6Net = "2001:db9:beef::/64".parse().unwrap();
///
/// let incoming_addr: Ipv6Addr = "2001:db9::feed".parse().unwrap();
/// let outcoming_addr_predicted: Ipv6Addr = "2001:db9:beef::feed".parse().unwrap();
///
/// let outcoming_addr = netmapv6(incoming_addr, &downstream_pfx);
/// let incoming_addr_reverted = netmapv6(outcoming_addr, &upstream_pfx);
///
/// assert_eq!(outcoming_addr, outcoming_addr_predicted);
/// assert_eq!(incoming_addr, incoming_addr_reverted);
/// ```
#[inline]
pub fn netmapv6(upstream_addr: Ipv6Addr, downstream_prefix: &Ipv6Net) -> Ipv6Addr {
    let net_u128 = u128::from_be_bytes(upstream_addr.octets())
        & u128::from_be_bytes(downstream_prefix.hostmask().octets());
    let prefix_u128 = u128::from_be_bytes(downstream_prefix.addr().octets())
        & u128::from_be_bytes(downstream_prefix.netmask().octets());
    Ipv6Addr::from((prefix_u128 + net_u128).to_be_bytes())
}
