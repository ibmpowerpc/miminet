import pytest

from conftest import MiminetTester
from utils.networks import MiminetTestNetwork


class TestPacketFilters:
    @pytest.fixture(scope="class")
    def network(self, selenium: MiminetTester):
        test_network = MiminetTestNetwork(selenium)

        yield test_network

        test_network.delete()

    def test_filter_does_not_restore_packets_after_reset(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return typeof SetPacketFilter === 'function' && typeof filterState !== 'undefined';"
            ),
            timeout=10,
        )

        # prepare cached packets and drop active player state, emulating SetNetworkPlayerState(-1)
        result = selenium.execute_script(
            """
            packets_not_filtered = [[{
                data: { id: 'pkt_1', label: 'ARP Broadcast', type: 'arp' },
                config: { path: 'edge_1', source: 'host_1', target: 'host_2' }
            }]];
            packets = null;
            filterState.hideARP = false;
            filterState.hideSTP = false;

            try {
                SetPacketFilter();
                return {
                    packets: packets,
                    cachedPacketsLength: packets_not_filtered.length
                };
            } catch (err) {
                return { error: err.toString() };
            }
            """
        )

        assert "error" not in result, f"JS error while filtering: {result['error']}"
        assert result["packets"] is None, "Stale packets resurrected after reset"
        assert (
            result["cachedPacketsLength"] == 1
        ), "Cache with original packets must stay untouched"

    def test_empty_packets_do_not_break_player(
        self, selenium: MiminetTester, network: MiminetTestNetwork
    ):
        selenium.get(network.url)
        selenium.wait_for(
            lambda driver: driver.execute_script(
                "return typeof SetPacketFilter === 'function' && typeof filterState !== 'undefined';"
            ),
            timeout=10,
        )

        result = selenium.execute_script(
            """
            packets = [];
            filterState.hideARP = true;
            filterState.hideSTP = true;

            try {
                SetPacketFilter();
                var slider = $('#PacketSliderInput')[0];
                return {
                    packets: packets,
                    sliderInitialized: Boolean(slider && slider.noUiSlider),
                    sliderVisible: slider ? $('#PacketSliderInput').is(':visible') : null,
                    labelText: $('#NetworkPlayerLabel').text()
                };
            } catch (err) {
                return { error: err.toString() };
            }
            """
        )

        assert "error" not in result, f"Packet filtering threw an error: {result['error']}"
        assert result["packets"] == [], "Filtered packets should stay empty"
        assert (
            result["sliderInitialized"] is False or result["sliderVisible"] is False
        ), "Slider must be hidden or uninitialized when nothing to play"
        assert result["labelText"] in (
            "",
            "0 пакетов",
        ), "Player label must reflect the empty state"
