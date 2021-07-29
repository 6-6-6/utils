use ipnet::Ipv6Net;
use std::net::Ipv6Addr;

/// construct an Ipv6Addr from a vector, make sure it conatins more than 16 elements!!
#[inline]
pub unsafe fn construct_v6addr(segments: &[u8]) -> Ipv6Addr {
    Ipv6Addr::from((*(segments.as_ptr() as *const u128)).to_be())
}

/// calculate checksum for NPTv6
pub fn pfx_csum(prefix: &Ipv6Net) -> u16 {
    let mut ret: i32 = 0;
    for x in prefix.network().segments().iter() {
        ret += *x as i32;
    }
    ((ret.rem_euclid(0xffff)) ^ 0xffff) as u16
}

/// see https://datatracker.ietf.org/doc/html/rfc6296
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

/// rewrite the prefix
#[inline]
pub fn netmapv6(upstream_addr: Ipv6Addr, downstream_prefix: &Ipv6Net) -> Ipv6Addr {
    let net_u128 = u128::from_be_bytes(upstream_addr.octets())
        & u128::from_be_bytes(downstream_prefix.hostmask().octets());
    let prefix_u128 = u128::from_be_bytes(downstream_prefix.addr().octets())
        & u128::from_be_bytes(downstream_prefix.netmask().octets());
    Ipv6Addr::from((prefix_u128 + net_u128).to_be_bytes())
}

//
#[test]
fn test_construct_addr() {
    let ref_result: Ipv6Addr = "2001:db8::1".parse().unwrap();
    let local_result = unsafe {
        construct_v6addr(&[
            0x20u8, 0x01, 0x0d, 0xb8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0x1,
        ])
    };
    assert_eq!(ref_result, local_result);
}

//TODO: more tests
