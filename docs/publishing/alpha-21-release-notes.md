# Alpha 21 Release Notes

## Fixed

- Prevented unchanged Home Assistant state updates from re-rendering the Club
  Royale card.
- Fixed filter dropdowns closing immediately when Home Assistant pushed a fresh
  but unchanged `hass` object to the card.
- Real sailing data changes still trigger a card render.
